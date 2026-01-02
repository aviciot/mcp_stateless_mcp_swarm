"""
MCP Swarm Load Test
===================
Heavy concurrent load test to verify Docker Swarm load balancing.

This script sends multiple concurrent requests to the MCP server
and tracks which replica handles each request, proving that the
stateless mode enables true horizontal scaling.

Usage:
    py -3.12 test_swarm_load.py
    py -3.12 test_swarm_load.py --requests 100 --concurrent 20
    py -3.12 test_swarm_load.py --url http://localhost:8150/mcp

Output:
    - Per-request results with replica hostname
    - Distribution statistics across replicas
    - Response time metrics
    - Success/failure rates
"""

import asyncio
import argparse
import time
import logging
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RequestResult:
    """Result of a single MCP request"""
    request_id: int
    success: bool
    hostname: Optional[str]
    response_time_ms: float
    error: Optional[str] = None


async def call_mcp_tool(
    client: httpx.AsyncClient,
    url: str,
    request_id: int,
    tool_name: str = "echo",
    arguments: dict = None
) -> RequestResult:
    """
    Call an MCP tool and track which replica handled it.
    Uses X-Served-By header to identify the handling replica.
    
    Args:
        client: HTTP client
        url: MCP server URL
        request_id: Unique request identifier
        tool_name: Name of the tool to call
        arguments: Tool arguments
    
    Returns:
        RequestResult with timing and replica info
    """
    if arguments is None:
        arguments = {"message": f"Load test request #{request_id}", "repeat": 1}
    
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    start_time = time.perf_counter()
    hostname = None
    
    try:
        # Make the MCP request
        response = await client.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30.0
        )
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # Get hostname from X-Served-By header (added by our middleware)
        hostname = response.headers.get("X-Served-By")
        
        if response.status_code == 200:
            return RequestResult(
                request_id=request_id,
                success=True,
                hostname=hostname,
                response_time_ms=elapsed_ms
            )
        else:
            return RequestResult(
                request_id=request_id,
                success=False,
                hostname=hostname,
                response_time_ms=elapsed_ms,
                error=f"HTTP {response.status_code}: {response.text[:100]}"
            )
            
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return RequestResult(
            request_id=request_id,
            success=False,
            hostname=None,
            response_time_ms=elapsed_ms,
            error=str(e)
        )


async def run_load_test(
    url: str,
    total_requests: int,
    concurrent_requests: int,
    delay_between_batches: float = 0.1
) -> list[RequestResult]:
    """
    Run concurrent load test against MCP server.
    
    Args:
        url: MCP server URL
        total_requests: Total number of requests to send
        concurrent_requests: Number of concurrent requests per batch
        delay_between_batches: Delay between batches (seconds)
    
    Returns:
        List of RequestResult for all requests
    """
    results = []
    
    logger.info(f"Starting load test: {total_requests} requests, {concurrent_requests} concurrent")
    logger.info(f"Target: {url}")
    
    async with httpx.AsyncClient() as client:
        request_id = 0
        
        while request_id < total_requests:
            # Create batch of concurrent requests
            batch_size = min(concurrent_requests, total_requests - request_id)
            tasks = []
            
            for i in range(batch_size):
                task = call_mcp_tool(
                    client=client,
                    url=url,
                    request_id=request_id + i,
                    arguments={
                        "message": f"Concurrent request #{request_id + i}",
                        "repeat": 1
                    }
                )
                tasks.append(task)
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Log progress
            completed = len(results)
            success_count = sum(1 for r in batch_results if r.success)
            logger.info(f"Batch complete: {completed}/{total_requests} requests ({success_count}/{batch_size} successful)")
            
            request_id += batch_size
            
            # Small delay between batches to avoid overwhelming
            if request_id < total_requests:
                await asyncio.sleep(delay_between_batches)
    
    return results


def analyze_results(results: list[RequestResult]) -> dict:
    """
    Analyze load test results and generate statistics.
    
    Args:
        results: List of RequestResult
    
    Returns:
        Dictionary with analysis statistics
    """
    total = len(results)
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    # Distribution by hostname (replica)
    hostname_counts = defaultdict(int)
    hostname_times = defaultdict(list)
    
    for r in successful:
        host = r.hostname or "unknown"
        hostname_counts[host] += 1
        hostname_times[host].append(r.response_time_ms)
    
    # Calculate response time stats
    all_times = [r.response_time_ms for r in successful]
    
    stats = {
        "total_requests": total,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / total * 100 if total > 0 else 0,
        "replica_distribution": dict(hostname_counts),
        "replica_count": len(hostname_counts),
        "response_times": {
            "min_ms": min(all_times) if all_times else 0,
            "max_ms": max(all_times) if all_times else 0,
            "avg_ms": sum(all_times) / len(all_times) if all_times else 0,
        },
        "errors": [r.error for r in failed if r.error][:10]  # First 10 errors
    }
    
    # Per-replica average response time
    stats["replica_avg_times"] = {
        host: sum(times) / len(times) 
        for host, times in hostname_times.items()
    }
    
    return stats


def print_report(stats: dict, duration_seconds: float):
    """Print formatted load test report"""
    
    print("\n" + "=" * 70)
    print("🏋️  MCP SWARM LOAD TEST REPORT")
    print("=" * 70)
    
    print(f"\n📊 SUMMARY")
    print(f"   Total Requests:     {stats['total_requests']}")
    print(f"   Successful:         {stats['successful']}")
    print(f"   Failed:             {stats['failed']}")
    print(f"   Success Rate:       {stats['success_rate']:.1f}%")
    print(f"   Test Duration:      {duration_seconds:.2f} seconds")
    print(f"   Throughput:         {stats['total_requests'] / duration_seconds:.1f} req/sec")
    
    print(f"\n⏱️  RESPONSE TIMES")
    print(f"   Min:                {stats['response_times']['min_ms']:.1f} ms")
    print(f"   Max:                {stats['response_times']['max_ms']:.1f} ms")
    print(f"   Average:            {stats['response_times']['avg_ms']:.1f} ms")
    
    print(f"\n🐳 REPLICA DISTRIBUTION (Proof of Load Balancing)")
    print(f"   Replicas Used:      {stats['replica_count']}")
    print("-" * 50)
    
    total_handled = sum(stats['replica_distribution'].values())
    for hostname, count in sorted(stats['replica_distribution'].items()):
        percentage = count / total_handled * 100 if total_handled > 0 else 0
        avg_time = stats['replica_avg_times'].get(hostname, 0)
        bar = "█" * int(percentage / 2)
        print(f"   {hostname[:12]:12} | {count:4} requests ({percentage:5.1f}%) | avg {avg_time:.0f}ms | {bar}")
    
    if stats['errors']:
        print(f"\n❌ ERRORS (first 10)")
        for i, error in enumerate(stats['errors'], 1):
            print(f"   {i}. {error[:60]}...")
    
    print("\n" + "=" * 70)
    
    # Verdict
    if stats['replica_count'] >= 2 and stats['success_rate'] >= 95:
        print("✅ VERDICT: Load balancing is WORKING! Multiple replicas handled requests.")
    elif stats['replica_count'] == 1 and stats['success_rate'] >= 95:
        print("⚠️  VERDICT: All requests went to ONE replica. Check Swarm VIP mode.")
    else:
        print("❌ VERDICT: Issues detected. Check errors above.")
    
    print("=" * 70 + "\n")


async def main():
    parser = argparse.ArgumentParser(
        description="MCP Swarm Load Test - Verify horizontal scaling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    py -3.12 test_swarm_load.py                          # Default: 50 requests, 10 concurrent
    py -3.12 test_swarm_load.py --requests 100           # 100 total requests
    py -3.12 test_swarm_load.py --concurrent 20          # 20 concurrent requests
    py -3.12 test_swarm_load.py -r 200 -c 50             # Heavy load: 200 requests, 50 concurrent
        """
    )
    parser.add_argument(
        "--url", "-u",
        default="http://localhost:8150/mcp",
        help="MCP server URL (default: http://localhost:8150/mcp)"
    )
    parser.add_argument(
        "--requests", "-r",
        type=int,
        default=50,
        help="Total number of requests (default: 50)"
    )
    parser.add_argument(
        "--concurrent", "-c",
        type=int,
        default=10,
        help="Number of concurrent requests (default: 10)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0.05,
        help="Delay between batches in seconds (default: 0.05)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("🚀 MCP SWARM LOAD TEST")
    print("=" * 70)
    print(f"   URL:                {args.url}")
    print(f"   Total Requests:     {args.requests}")
    print(f"   Concurrent:         {args.concurrent}")
    print(f"   Started:            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    # Run the load test
    start_time = time.perf_counter()
    results = await run_load_test(
        url=args.url,
        total_requests=args.requests,
        concurrent_requests=args.concurrent,
        delay_between_batches=args.delay
    )
    duration = time.perf_counter() - start_time
    
    # Analyze and report
    stats = analyze_results(results)
    print_report(stats, duration)
    
    # Return exit code based on success
    return 0 if stats['success_rate'] >= 95 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
