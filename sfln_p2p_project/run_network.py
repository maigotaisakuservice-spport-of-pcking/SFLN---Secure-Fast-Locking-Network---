import asyncio
import os
import time
import sys
import re

# --- Configuration ---
DEVICES_TO_RUN = {
    "Device-A": 9001,
    "Device-B": 9002,
    "Device-C": 9003,
    "Device-D": 9004,
}
LOG_DIR = "sfln_p2p_project"
PHASE_1_DURATION = 18  # Time for network to form (2 scan cycles)
UNSAFE_DEVICE_NAME = "Device-C"
UNSAFE_TIMER = 15 # C becomes unsafe after 15s
PHASE_2_DURATION = 18  # Time after unsafe event for network to heal

def read_log_file(log_path):
    """Reads the entire content of a log file, ignoring file not found errors."""
    try:
        with open(log_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return ""

async def verify_phase_1():
    print("\n--- Verifying Phase 1: Network Formation ---")
    all_passed = True
    for name in DEVICES_TO_RUN.keys():
        print(f"\n--- Verifying {name}'s Log ---")
        log_content = read_log_file(os.path.join(LOG_DIR, f"device-{name}.log"))

        if not log_content:
            print(f"  ❌ FAILURE: Log file for {name} is empty or not found.")
            all_passed = False
            continue

        # Check 1: Did it connect to all other peers?
        try:
            # Find the last "Current peers" log entry before the unsafe event
            all_lines = log_content.strip().split('\n')

            # Get lines before the unsafe message if it exists
            unsafe_line_index = next((i for i, line in enumerate(all_lines) if "UNSAFE" in line), len(all_lines))
            relevant_lines = [line for line in all_lines[:unsafe_line_index] if "Current peers" in line]

            if not relevant_lines: raise IndexError("No peer status line found")

            last_peers_line = relevant_lines[-1]
            peer_list_str = last_peers_line.split("Current peers: ")[1]
            connected_peers = set(eval(peer_list_str))

            expected_peers = set(DEVICES_TO_RUN.keys()) - {name}
            if connected_peers == expected_peers:
                print(f"  ✅ SUCCESS: {name} connected to all {len(expected_peers)} peers.")
            else:
                print(f"  ❌ FAILURE: {name} expected peers {list(expected_peers)} but has {list(connected_peers)}.")
                all_passed = False
        except Exception as e:
            print(f"  ❌ FAILURE: Could not parse peer list for {name}. Error: {e}")
            all_passed = False

        # Check 2: Did it calculate a routing table for all other peers?
        if "New routing table" in log_content:
             print(f"  ✅ SUCCESS: {name} calculated a routing table.")
        else:
             print(f"  ❌ FAILURE: {name} did not calculate a routing table.")
             all_passed = False

    return all_passed

async def verify_phase_2():
    print("\n--- Verifying Phase 2: Network Healing ---")
    all_passed = True

    # Verify the unsafe device's log
    unsafe_log_path = os.path.join(LOG_DIR, f"device-{UNSAFE_DEVICE_NAME}.log")
    unsafe_log_content = read_log_file(unsafe_log_path)
    if "DEVICE IS NOW UNSAFE" in unsafe_log_content:
        print(f"  ✅ SUCCESS: {UNSAFE_DEVICE_NAME} correctly logged its unsafe shutdown.")
    else:
        print(f"  ❌ FAILURE: {UNSAFE_DEVICE_NAME} did not log its unsafe shutdown.")
        all_passed = False

    # Verify remaining devices
    remaining_devices = {name for name in DEVICES_TO_RUN if name != UNSAFE_DEVICE_NAME}
    for name in remaining_devices:
        print(f"\n--- Verifying {name}'s Log ---")
        log_content = read_log_file(os.path.join(LOG_DIR, f"device-{name}.log"))

        if f"Removed peer '{UNSAFE_DEVICE_NAME}'" in log_content or f"Connection with {UNSAFE_DEVICE_NAME} lost" in log_content:
            print(f"  ✅ SUCCESS: {name} logged disconnection from {UNSAFE_DEVICE_NAME}.")
        else:
            print(f"  ❌ FAILURE: {name} did not log disconnection from {UNSAFE_DEVICE_NAME}.")
            all_passed = False

        try:
            last_routing_table_lines = [line for line in log_content.strip().split('\n') if "New routing table" in line]
            if not last_routing_table_lines: raise IndexError("No routing table found")

            last_routing_table_line = last_routing_table_lines[-1]
            table_str = last_routing_table_line.split("New routing table: ")[1]
            routing_table = eval(table_str)
            if len(routing_table) == len(remaining_devices) - 1:
                print(f"  ✅ SUCCESS: {name} has a new routing table with {len(routing_table)} entries.")
            else:
                print(f"  ❌ FAILURE: {name} has incorrect number of routes ({len(routing_table)}). Expected {len(remaining_devices) - 1}")
                all_passed = False
        except Exception as e:
            print(f"  ❌ FAILURE: Could not parse final routing table for {name}. Error: {e}")
            all_passed = False

    return all_passed


async def main():
    print("--- SFLN Network Simulation Runner ---")
    os.makedirs(LOG_DIR, exist_ok=True)
    for name in DEVICES_TO_RUN.keys():
        log_file = os.path.join(LOG_DIR, f"device-{name}.log")
        if os.path.exists(log_file): os.remove(log_file)

    processes = {}
    try:
        # --- Launch Devices ---
        print("[*] Launching SFLN device processes...")
        script_path = os.path.join(os.path.dirname(__file__), 'device.py')
        for name, port in DEVICES_TO_RUN.items():
            cmd = [sys.executable, script_path, name, str(port)]
            # THIS IS THE CRITICAL FIX: Pass the --test-unsafe-after argument
            if name == UNSAFE_DEVICE_NAME:
                cmd.extend(["--test-unsafe-after", str(UNSAFE_TIMER)])
                print(f"    - Launching {name} on port {port} (unsafe in {UNSAFE_TIMER}s)")
            else:
                print(f"    - Launching {name} on port {port}")

            proc = await asyncio.create_subprocess_exec(*cmd)
            processes[name] = proc

        # --- Phase 1: Network Formation ---
        print(f"\n[PHASE 1] Network forming. Waiting {PHASE_1_DURATION} seconds...")
        await asyncio.sleep(PHASE_1_DURATION)
        if not await verify_phase_1():
            raise Exception("Phase 1 (Network Formation) failed.")
        print("\n[SUCCESS] Phase 1 verification passed.")

        # --- Phase 2: Network Healing ---
        print(f"\n[PHASE 2] Waiting for '{UNSAFE_DEVICE_NAME}' to go unsafe and network to heal...")
        # We already waited 15s, unsafe timer is 15s, so it should have just triggered.
        # Wait for routing updates to propagate.
        await asyncio.sleep(PHASE_2_DURATION)

        if not await verify_phase_2():
            raise Exception("Phase 2 (Network Healing) failed.")

        print("\n---------------------------------")
        print("✅✅✅ OVERALL RESULT: SUCCESS ✅✅✅")
        print("P2P network formed, routed, and healed successfully.")
        print("---------------------------------")

    except Exception as e:
        print(f"\n❌❌❌ OVERALL RESULT: FAILURE: {e} ❌❌❌")
    finally:
        print("\n[*] Cleaning up remaining processes...")
        for proc in processes.values():
            if proc.returncode is None:
                try: proc.terminate(); await asyncio.wait_for(proc.wait(), 2.0)
                except asyncio.TimeoutError: proc.kill()
        print("[*] Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
