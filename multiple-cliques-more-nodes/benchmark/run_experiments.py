import os
import subprocess
import time

# Function to run the setup and experiment
def run_experiment(a_value, experiment_num, num_nodes=31, log_dir='logs', experiment_dir='experiment_logs_aws'):
    # Create a unique experiment directory to store logs for each value of 'a' and experiment number
    experiment_folder = os.path.join(experiment_dir, f'a_{a_value}_{experiment_num}')
    os.makedirs(experiment_folder, exist_ok=True)
    
    # Step 1: Run the setup script with the specified 'a' value
    setup_command = [
        'python3', 'setup-env.py', 
        '-n', str(num_nodes),  # Number of nodes
        '-l', '7',              # Some fixed parameter (log level, as per your example)
        '-c', '2',              # Some fixed parameter (could be clients, as per your example)
        '-a', str(a_value)     # Varying 'a' value
    ]
    print(f"Running setup with a = {a_value} for experiment {experiment_num}...")
    try:
        subprocess.run(setup_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running setup for a = {a_value} (experiment {experiment_num}): {e}")
        return
    
    # Step 2: Run the experiment using 'fab localmal' and capture the logs
    print(f"Running experiment with fab localmal for a = {a_value} (experiment {experiment_num})...")
    try:
        subprocess.run(['fab', 'remotemal'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running fab localmal for a = {a_value} (experiment {experiment_num}): {e}")
        return
    
    # Step 3: Move logs to the experiment folder with a timestamp
    print(f"Saving logs for a = {a_value}, experiment {experiment_num}...")
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    
    # Move the logs to the experiment folder
    logs_source_dir = 'logs'  # Directory where logs are stored
    for node_id in range(num_nodes):
        log_filename = os.path.join(logs_source_dir, f'node-{node_id}.log')
        if os.path.exists(log_filename):
            dest_filename = os.path.join(experiment_folder, f'node-{node_id}.log')
            os.rename(log_filename, dest_filename)
        else:
            print(f"Log file node-{node_id} not found!")

    print(f"Logs for a = {a_value}, experiment {experiment_num} saved in {experiment_folder}\n")

# Main function to run multiple experiments
def run_multiple_experiments():
    start_a = 200
    end_a = 250
    increment = 50
    num_runs = 1  # Number of times to run each experiment

    # Directory to store all experiment logs
    experiment_dir = 'experiment_logs_aws'
    os.makedirs(experiment_dir, exist_ok=True)
    
    # Run experiments for each 'a' value from 40 to 120 with increment of 10
    for a_value in range(start_a, end_a + 1, increment):
        # Run the experiment multiple times for the same 'a_value'
        for experiment_num in range(1, num_runs + 1):
            run_experiment(a_value, experiment_num)
    
    print("All experiments finished!")

if __name__ == '__main__':
    run_multiple_experiments()

