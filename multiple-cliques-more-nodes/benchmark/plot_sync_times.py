import os
import time
import matplotlib.pyplot as plt
from statistics import mean
from re import findall, search
from datetime import datetime

def extract_sync_times_from_logs(log_dir, num_nodes=31):
    start_sync = []
    end_sync = []
    alt_chain_length = []

    # Loop through each node's log file and extract sync times
    for node_id in range(num_nodes):
        log_filename = os.path.join(log_dir, f'node-{node_id}.log')
        if os.path.exists(log_filename):
            with open(log_filename, 'r') as log_file:
                log_content = log_file.read()

                # Find first occurrence of start and end sync times using regex
                start_sync_match = search(r'\[(.*Z) .* Sending new sync request to this.', log_content)
                end_sync_match = search(r'\[(.*Z) .* Finished recovery procedur.', log_content)

                alt_chain_match = search(r'Length of alt chain here is (\d+)', log_content)
                # Check if both start and end sync times are found
                if start_sync_match and end_sync_match:
                    start_sync.append(start_sync_match.group(1))  # Extract the timestamp from the match
                    end_sync.append(end_sync_match.group(1))      # Extract the timestamp from the match
                    alt_chain_match.append(alt_chain_match.group(1))
                else:
                    # If either start or end sync is missing, print a warning for that node
                    print(f"Warning: Node {node_id} has missing sync times (start or end). Skipping this node.")
                    print(f"Node {node_id} - Start sync found: {bool(start_sync_match)}, End sync found: {bool(end_sync_match)}")

        else:
            print(f"Log file for node {node_id} not found.")

    # Ensure we only return matching pairs
    if len(start_sync) != len(end_sync):
        print("Warning: Mismatch between total start and end sync times.")

    # Convert timestamps to POSIX time (if necessary, depending on how your logs are formatted)
    start_sync = [to_posix(t) for t in start_sync]
    end_sync = [to_posix(t) for t in end_sync]

    return start_sync, end_sync

# Convert ISO 8601 timestamp to POSIX timestamp
def to_posix(string):
    x = datetime.fromisoformat(string.replace('Z', '+00:00'))
    return datetime.timestamp(x)

# Function to calculate the average sync time (end_sync - start_sync)
def calculate_average_sync_time(start_sync, end_sync):
    sync_times = []
    for s, e in zip(start_sync, end_sync):
        sync_times.append(e - s)
    return mean(sync_times) if sync_times else 0

# Main function to generate the plot
def plot_average_sync_time():
    experiment_dir = 'experiment_logs'  # Directory where all experiments are stored
    a_values = range(2, 6)       # Values of 'a' to consider
    avg_sync_times = []

    # Loop through each experiment and calculate the average sync time
    for a_value in a_values:
        experiment_folder = os.path.join(experiment_dir, f'ib_{a_value}')
        if os.path.exists(experiment_folder):
            # Extract sync times from logs for this experiment
            start_sync, end_sync, alt_chain_length = extract_sync_times_from_logs(experiment_folder)
            
            # Calculate average sync time for this experiment
            avg_sync_time = calculate_average_sync_time(start_sync, end_sync)
            print("Avg time is " + str(avg_sync_time))
            avg_sync_times.append(avg_sync_time)
        else:
            print(f"Logs for a = {a_value} not found!")

    # Plotting the results
    plt.figure(figsize=(10, 6))
    plt.plot(a_values, avg_sync_times, marker='o', linestyle='-', color='b', label='Average Sync Time')

    plt.title('Average Sync Time vs. a', fontsize=16)
    plt.xlabel('a (Parameter Value)', fontsize=14)
    plt.ylabel('Average Sync Time (seconds)', fontsize=14)
    plt.grid(True)
    plt.xticks(a_values)  # Ensure the x-axis shows each 'a' value
    plt.tight_layout()

    # Show the plot
    plt.savefig('parameter_value.pdf', dpi=300)

# Function to group sync times by alt chain length and calculate the average time per block
def group_by_alt_chain_length(alt_chain_lengths, start_sync, end_sync):
    block_times = defaultdict(list)

    # Group sync times by alt chain length (blocks)
    for blocks, s, e in zip(alt_chain_lengths, start_sync, end_sync):
        if blocks is not None and s is not None and e is not None:
            block_times[blocks].append(e - s)

    # Calculate the average sync time for each block count
    avg_block_times = {blocks: mean(times) for blocks, times in block_times.items()}

    return avg_block_times

# Main function to generate the scatter plot
def plot_avg_sync_time_vs_blocks(experiment_dir='experiment_logs', output_file='blocks_vs_time.pdf'):
    # Create a dictionary to store all the block times
    all_avg_block_times = {}

    # Extract sync times and alt chain lengths from logs for the experiment
    start_sync, end_sync, alt_chain_lengths_for_exp = extract_sync_times_from_logs(experiment_dir)
            
    # Group by block size and calculate average sync times for each block size
    avg_block_times = group_by_alt_chain_length(alt_chain_lengths_for_exp, start_sync, end_sync)
    print(f"Avg block times: {avg_block_times}")
    
    # Plotting the results using scatter plot
    plt.figure(figsize=(10, 6))

    # Extract block lengths (x-axis) and their corresponding average sync times (y-axis)
    block_lengths = sorted(avg_block_times.keys())
    avg_times = [avg_block_times[block] for block in block_lengths]

    # Scatter plot
    plt.scatter(block_lengths, avg_times, color='b', label='Avg Sync Time')

    plt.title('Average Sync Time vs. Number of Blocks', fontsize=16)
    plt.xlabel('Number of Blocks', fontsize=14)
    plt.ylabel('Average Sync Time (seconds)', fontsize=14)
    plt.grid(True)
    plt.tight_layout()

    # Save the plot to a file
    plt.savefig(output_file, dpi=300)

if __name__ == '__main__':
    plot_average_sync_time()
    #plot_avg_sync_time_vs_blocks(experiment_dir='experiment_logs', output_file='blocks_vs_time.pdf')
