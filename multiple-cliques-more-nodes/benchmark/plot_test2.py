import os
import time
import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib
from statistics import mean
from re import search
from datetime import datetime
from collections import defaultdict
import scipy.stats as stats

# Function to extract sync times, alt chain lengths, and recovery times from log files
def extract_sync_times_and_alt_chain_lengths(log_dir, num_nodes=31):
    start_sync = []
    end_sync = []
    alt_chain_lengths = []  # List to store the length of the alt chain
    end_rec = []  # List to store recovery times

    # Loop through each node's log file and extract sync times, alt chain lengths, and recovery times
    for node_id in range(num_nodes):
        log_filename = os.path.join(log_dir, f'node-{node_id}.log')
        if node_id == 6:
            continue
        if os.path.exists(log_filename):
            with open(log_filename, 'r') as log_file:
                log_content = log_file.read()

                # Find first occurrence of start and end sync times using regex
                start_sync_match = search(r'\[(.*Z) .* Sending new sync request to this.', log_content)
                end_sync_match = search(r'\[(.*Z) .* Length of alt chain h*', log_content)
                end_rec_match = search(r'\[(.*Z) .* Finished recovery procedu*', log_content)

                # Find the length of the alt chain using regex
                alt_chain_match = search(r'Length of alt chain here is (\d+)', log_content)

                # Check if both start and end sync times are found
                if start_sync_match and end_sync_match:
                    if alt_chain_match:
                        if int(alt_chain_match.group(1)) > 2:
                            start_sync.append(start_sync_match.group(1))  # Extract the timestamp from the match
                            end_sync.append(end_sync_match.group(1))      # Extract the timestamp from the match
                            if end_rec_match:
                                if math.ceil(math.log(int(alt_chain_match.group(1)), 2)) != 8:
                                    end_rec.append(end_rec_match.group(1))  # Add the recovery time
                            else:
                                if math.ceil(math.log(int(alt_chain_match.group(1)), 2)) == 8:
                                    end_rec_match = search(r'\[(.*Z) .* Firewall after adding*', log_content)
                                    end_rec.append(end_rec_match.group(1))  # Add the recovery time


                else:
                    print(f"Warning: Node {node_id} has missing sync times (start or end). Skipping this node.")
                    print(f"Node {node_id} - Start sync found: {bool(start_sync_match)}, End sync found: {bool(end_sync_match)}")

                # If the alt chain length is found, store it, else store None
                if alt_chain_match:
                        if int(alt_chain_match.group(1)) > 2:
                            alt_chain_lengths.append(math.ceil(math.log(int(alt_chain_match.group(1)), 2)))  # Store the log of the alt chain length
                else:
                    print(f"Warning: Node {node_id} has no alt chain length information.")
                    alt_chain_lengths.append(None)

        else:
            print(f"Log file for node {node_id} not found.")

    # Ensure we only return matching pairs
    if len(start_sync) != len(end_sync):
        print("Warning: Mismatch between total start and end sync times.")

    # Convert timestamps to POSIX time
    start_sync = [to_posix(t) for t in start_sync]
    end_sync = [to_posix(t) for t in end_sync]
    end_rec = [to_posix(t) for t in end_rec]  # Convert recovery times to POSIX, skip None

    return start_sync, end_sync, alt_chain_lengths, end_rec

# Convert ISO 8601 timestamp to POSIX timestamp
def to_posix(string):
    try:
        x = datetime.fromisoformat(string.replace('Z', '+00:00'))
        return datetime.timestamp(x)
    except Exception as e:
        print(f"Error converting time {string}: {e}")
        return None

# Function to calculate the average sync time (end_sync - start_sync)
def calculate_average_sync_time(start_sync, end_sync):
    sync_times = []
    for s, e in zip(start_sync, end_sync):
        if s is not None and e is not None:
            sync_times.append(e - s)
    return mean(sync_times) if sync_times else 0

# Function to group sync times by alt chain length and calculate the average time per block
def group_by_alt_chain_length(alt_chain_lengths, start_sync, end_sync, end_rec):
    block_times = defaultdict(list)
    block_rec_times = defaultdict(list)

    # Group sync times by alt chain length (blocks)
    for blocks, s, e, rec in zip(alt_chain_lengths, start_sync, end_sync, end_rec):
        if blocks is not None and s is not None and e is not None:
            block_times[blocks].append(e - s)
            if rec is not None:
                block_rec_times[blocks].append(rec - s)

    # Calculate the average sync time for each block count
    avg_block_times = {blocks: mean(times) for blocks, times in block_times.items()}
    # Calculate the average recovery time for each block count
    avg_rec_times = {blocks: mean(times) for blocks, times in block_rec_times.items()}
    print(avg_rec_times)

    # Calculate the standard error (std deviation / sqrt(n)) for each block count
    block_errors = {blocks: stats.sem(times) for blocks, times in block_times.items()}
    block_rec_errors = {blocks: stats.sem(times) for blocks, times in block_rec_times.items()}

    return avg_block_times, block_errors, avg_rec_times, block_rec_errors

# Main function to generate the scatter plot
def plot_avg_sync_time_vs_blocks(experiment_dir='experiment_logs', output_file='blocks_vs_time.pdf'):
    avg_block_times_all = defaultdict(list)
    block_errors_all = defaultdict(list)
    avg_rec_times_all = defaultdict(list)
    block_rec_errors_all = defaultdict(list)

    matplotlib.rcParams['text.usetex'] = True

    # Iterate through the directories inside experiment_logs
    for a_dir in os.listdir(experiment_dir):
        a_dir_path = os.path.join(experiment_dir, a_dir)
        if a_dir == 'a_200_1':
            continue
        
        # Only process directories, skip non-directory files
        if os.path.isdir(a_dir_path):
            print(f"Processing directory: {a_dir_path}")
            
            # Extract sync times, alt chain lengths, and recovery times from logs in the current directory
            start_sync, end_sync, alt_chain_lengths, end_rec = extract_sync_times_and_alt_chain_lengths(a_dir_path)
            
            # Group by block size and calculate average sync times and recovery times for each block size
            avg_block_times, block_errors, avg_rec_times, block_rec_errors = group_by_alt_chain_length(alt_chain_lengths, start_sync, end_sync, end_rec)
            
            # Store the results for this directory
            for block_length, avg_time in avg_block_times.items():
                avg_block_times_all[block_length].append(avg_time)
            for block_length, error in block_errors.items():
                block_errors_all[block_length].append(error)
            for block_length, avg_rec_time in avg_rec_times.items():
                avg_rec_times_all[block_length].append(avg_rec_time)
            for block_length, rec_error in block_rec_errors.items():
                block_rec_errors_all[block_length].append(rec_error)
    
    # Calculate the average sync time for each block length across all directories
    avg_block_times_overall = {block_length: mean(times) for block_length, times in avg_block_times_all.items()}
    block_errors_overall = {block_length: mean(errors) for block_length, errors in block_errors_all.items()}
    
    avg_rec_times_overall = {block_length: mean(times) for block_length, times in avg_rec_times_all.items()}
    block_rec_errors_overall = {block_length: mean(errors) for block_length, errors in block_rec_errors_all.items()}

    # Plotting the results using scatter plot
    #plt.figure(figsize=(10, 6))

    # Extract block lengths (x-axis) and their corresponding average sync times (y-axis)
    block_lengths = sorted(avg_block_times_overall.keys())
    avg_times = [avg_block_times_overall[block] for block in block_lengths]
    print("Avg block times:")
    print(avg_times)
    #errors = [block_errors_overall[block] for block in block_lengths]

    # Scatter plot for sync time
    #plt.plot(block_lengths, avg_times, color='b', marker='.', label='Average Retrieval Time', zorder=5)

    # Scatter plot for recovery time
    avg_rec_times = [avg_rec_times_overall[block] for block in block_lengths]
    print("Avg rec times:")
    print(avg_rec_times)
    #rec_errors = [block_rec_errors_overall[block] for block in block_lengths]
    plt.plot(block_lengths, avg_rec_times, lw=2, color='g', marker='v', label='Average Recovery Time', zorder=5)

    # Plotting error bars for the confidence intervals (standard error)
    #plt.errorbar(block_lengths, avg_times, yerr=errors, fmt='o', color='b', capsize=5, zorder=3)
    #plt.errorbar(block_lengths, avg_rec_times, yerr=rec_errors, fmt='o', color='g', capsize=5, zorder=3)

    # Set log scale for x-axis
    #plt.xscale('log')

    # Title and labels
    #plt.title('Average Sync Time vs. Number of Blocks', fontsize=16)
    plt.xticks([2, 3, 4, 5, 6])
    #plt.xlabel('ceiling(log L)', fontsize=14)
    plt.xlabel(r'$\lceil \log L \rceil$', fontsize=14)
    plt.ylabel('Average Recovery Time (seconds)', fontsize=14)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.grid(True)
    plt.tight_layout()

    # Show legend
    #plt.legend()

    # Save the plot to a file
    plt.savefig(output_file, dpi=300)

if __name__ == '__main__':
    plot_avg_sync_time_vs_blocks(experiment_dir='experiment_logs_aws', output_file='blocks_vs_time_retrieval_and_recovery.pdf')

