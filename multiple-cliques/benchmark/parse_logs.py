from datetime import datetime
from glob import glob
from multiprocessing import Pool
from os.path import join
from re import findall, search
from statistics import mean
from collections import Counter
import pandas as pd
import sys
import matplotlib.pyplot as plt

from benchmark.utils import Print

def parse_nodes(log):
    if search(r'panic', log) is not None:
        raise Exception('Node(s) panicked')

    tmp = findall(r'\[(.*Z) .* Created B\d+ -> ([^ ]+=)', log)
    tmp = [(d, to_posix(t)) for t, d in tmp]
    proposals = merge_results([tmp])

    tmp = findall(r'\[(.*Z) .* Committed B\d+ -> ([^ ]+=)', log)
    tmp = [(d, to_posix(t)) for t, d in tmp]
    commits = merge_results([tmp])
    
    tmp = findall(r'\[(.*Z) .* Committed B(\d+) -> ([^ ]+=)', log)
    tmp = [(to_posix(time), d, t) for time, t, d in tmp]
    blocks = tmp

    tmp = findall(r'\[(.*Z) .* Sending new sync request to this.', log)
    tmp = [to_posix(t) for t in tmp]
    start_sync = tmp
#    print('Start: ' + str(start_sync) + ' in log ' + str(log[:57]))

    tmp = findall(r'\[(.*Z) .* Updated Firewall, which now is.', log)
    tmp = [to_posix(t) for t in tmp]
    end_sync = tmp
 #   print('End: ' + str(end_sync) + ' in log ' + str(log[:57]))

    tmp = findall(r'Batch ([^ ]+) contains (\d+) B', log)
    sizes = {d: int(s) for d, s in tmp}

    tmp = findall(r'Batch ([^ ]+) contains sample tx (\d+)', log)
    samples = {int(s): d for d, s in tmp}
    
    return proposals, commits, sizes, start_sync, end_sync, samples, blocks

def parse_clients(log):
    if search(r'Error', log) is not None:
        raise ParseError('Client(s) panicked')

    size = int(search(r'Transactions size: (\d+)', log).group(1))
    rate = int(search(r'Transactions rate: (\d+)', log).group(1))

    tmp = search(r'\[(.*Z) .* Start ', log).group(1)
    start = to_posix(tmp)

    misses = len(findall(r'rate too high', log))

    tmp = findall(r'\[(.*Z) .* sample transaction (\d+)', log)
    samples = {int(s): to_posix(t) for t, s in tmp}

    return size, rate, start, misses, samples


def consensus_throughput(commits, proposals, sizes, size):
    if not commits:
        return 0, 0, 0
    start, end = min(proposals.values()), max(commits.values())
    duration = end - start
    bytes = sum(sizes.values())
    bps = bytes / duration
    tps = bps / size[0]
    return tps, bps, duration

def end_to_end_latency(commits, sent_samples, received_samples):
    latency = []
    for sent, received in zip(sent_samples, received_samples):
        for tx_id, batch_id in received.items():
            if batch_id in commits:
                if tx_id in sent:
                    start = sent[tx_id]
                    end = commits[batch_id]
                    latency += [end-start]
    #print(latency)
    return mean(latency) if latency else 0


def to_posix(string):
    x = datetime.fromisoformat(string.replace('Z', '+00:00'))
    return datetime.timestamp(x)

def log_filename(nodes):
    files = ['./logs/node-' + str(i) +'.log' for i in range(nodes)]
    return files

def clients_filename(nodes):
    files = ['./logs/client-' + str(i) +'.log' for i in range(nodes)]
    return files

def merge_results(input):
    # Keep the earliest timestamp.
    merged = {}
    for x in input:
        for k, v in x:
            if not k in merged or merged[k] > v:
                merged[k] = v
    return merged

def count_commits_in_intervals(commits):
    if not commits:
        return {}

    interval_length = 5  # seconds
    interval_counts = {}

    for commit_time, _ in commits:
        interval_start = commit_time
        #interval_counts[interval_start] =

    return interval_counts


def main():
    if len(sys.argv) < 2:
        print("Please enter the number of nodes as arguments")
        print("USAGE: python3 parse_nodes.py <nodes>")
        return -1
    files = log_filename(int(sys.argv[1]))
    logs = []
    for file in files:
        with open(file, 'r') as f:
            logs += [f.read()]

    try:
        with Pool() as p:
            results = p.map(parse_nodes, logs)
            results_two = p.map(parse_nodes, [logs[2]])
    except (ValueError, IndexError) as e:
        raise Exception(f'Failed to parse node logs: {e}')

    proposals, commit, sizes, start_all, end_all, received_samples, blocks_all \
        = zip(*results)

    #commits = merge_results([x.items() for x in commit])
    #counter = Counter(commits.values())

    proposals_two, commit_two, sizes_two, start_sync, end_sync, received_two, blocks_two \
        = zip(*results_two)
    test_two = merge_results([x.items() for x in commit_two])
    sizes_test = [x.items() for x in sizes]
    sizes_two = merge_results(sizes_test)
    counter_two = Counter(test_two.values())
    commit_two = {k: v for k, v in sorted(test_two.items(), key=lambda item: item[1])}
    execution_time = max(commit_two.values())-min(commit_two.values())
    
    

    start = []
    end = []
    for x in start_sync:
        for y in x:
            start.append(y)
    for x in end_sync:
        for y in x:
            end.append(y)

    print(start)
    print(end)
    start_vec = []
    end_vec = []
    start_time = min(start)-min(commit_two.values())
    end_time = max(end)-min(commit_two.values())
    min_time = min(commit_two.values())
    print('Min time is ' + str(min_time))
    print(start_time)
    print(end_time)
    #print(commit_two)
    #return
 ####################################### Block graph #################################################
    blocks = {}
    blocks_time = {}
    for time, batch_id, block in blocks_two[0]:
        if block not in blocks:
            blocks[block] = []
            blocks_time[block] = time - min(commit_two.values())
        if time - min_time > blocks_time[block] + 1:
            if block+'_test' not in blocks:
                blocks[block+'_test'] = []
                blocks_time[block+'_test'] = time - min_time
            blocks[block+'_test'].append(batch_id)
        else:
            blocks[block].append(batch_id)

    print(blocks.keys())
    print(blocks_time)
    
    block_timestamp = []
    block_sizes = []
    block_zero = []
    for block in blocks:
        block_timestamp.append(blocks_time[block])
        block_zero.append(blocks[block][0])
        block_size = 0
        for value in blocks[block]:
            block_size += sizes_two[value]
        block_sizes.append(block_size/512)
    print('\n\n\n')
    print(block_timestamp)
    print(block_sizes)
    print('\n\n\n')

   
    plt.clf()
    plt.scatter(block_timestamp, block_sizes)
    plt.grid()
    #plt.xscale('log')
    plt.title('Node 0')
    plt.ylabel('Number of transactions')
    plt.xlabel('Commit Time (s)')
    for i in range(len(start)):
        plt.axvspan(start[0]-min(commit_two.values()), end[0]-min(commit_two.values()), color='blue', alpha=0.95, lw=0)
    ax = plt.gca()
    plt.tight_layout()
    plt.savefig('block_commit-node2.pdf')
    plt.clf()
    #return
########################################################################################################
    batches = []
    timestamp = []
    for key in commit_two:
        batches.append(key)
        timestamp.append(commit_two[key]-min_time)

    batch_size = []
    for batch in batches:
        batch_size.append(sizes_two[batch]/512)

    dic = {}
    i = 0
    for time in timestamp:
        if time not in dic:
            dic[time] = []
        dic[time].append(batch_size[i])
        dic[time] = [sum(dic[time])]
        i+=1

    for batch in batch_size:
        if batch == 1:
            print(batch)
    print('\n\n\n\n\n\n\n\n\n\n\n\n')
    #print(dic)
    print('\n\n\n\n\n\n\n\n\n\n\n\n')
    plt.scatter(list(dic.keys()), list(dic.values()))
    plt.grid()
    plt.ylabel('Number of transactions')
    plt.xlabel('Commit Time (s)')
    for i in range(len(start)):
        plt.axvspan(start[0]-min(commit_two.values()), end[0]-min(commit_two.values()), color='blue', alpha=0.15, lw=0)
    ax = plt.gca()
    plt.savefig('transactions_time.pdf')
    plt.clf()

    tps = []
    x = []
    #for i in range(1,int(execution_time) + 2, 1):
    #    x.append(i)
    #    bps_accumulator = 0
    #    for key in commit_two:
    #        if commit_two[key] - min_time > i - 1 and commit_two[key] - min_time < i:
    #            bps_accumulator += sizes_two[key]
    #    tps.append(bps_accumulator/512)
    
    print('\n\n\n\n\n\n')
    for i in range(1,int(execution_time) + 2, 1):
        x.append(i)
        bps_accumulator = 0
        for time, batch_id, block in blocks_two[0]:
            if time - min_time >= (i - 1) and time - min_time < i:
                bps_accumulator += sizes_two[batch_id]
        tps.append(bps_accumulator/512)

    for idx, i in enumerate(tps):
        if i != 0:
            print(idx)
    print('\n\n\n\n\n')

    plt.clf()
    plt.plot(x, tps, lw=2)
    ax = plt.gca()
    #ax.set_xticks([i for i in range(30, 300, 60)])
    #ax.set_xticklabels(['[15,30]', '[75,90]', '[135,150]', '[195,210]', '[255,270]'])
    plt.grid()
    plt.title('Node 2', fontsize=16)
    plt.ylabel('Number of transactions', fontsize=14)
    plt.ylim(top=12000000)
    plt.xlabel('Time (s)', fontsize=14)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    ax.yaxis.get_offset_text().set_fontsize(14)
    for i in range(len(start)):
        plt.axvline(start[i]-min(commit_two.values()), color='tab:red', lw=2, ls='dashed')
    #plt.axvspan(start_time, end_time, color='blue', alpha=0.15, lw=0)
    plt.tight_layout()
    #plt.savefig('tps_recovery-nodeX.pdf', dpi=300)
    plt.clf()

    #x, y = [], []
    #for value in counter_two:
    #    x += [value]
    #    y += [counter_two[value]]

    #x = [i-x[0] for i in x]
    #print('x: ' + str(x))
    #print('y: ' + str(y))
    #plt.scatter(x,y)
    #plt.grid()
    #plt.ylabel('Number of commits')
    #plt.xlabel('Time (s)')
    #plt.axvspan(start_time, end_time, color='blue', alpha=0.15, lw=0)
    #plt.savefig('number_commits.pdf')

    files = clients_filename(int(sys.argv[1]))
    logs = []
    for file in files:
        with open(file, 'r') as f:
            logs += [f.read()]

    try:
        with Pool() as p:
            results = p.map(parse_clients, logs)
    except (ValueError, IndexError) as e:
        raise ParseError(f'Failed to parse client logs: {e}')
    size_client, rate, start_client, misses, sent_samples \
        = zip(*results)

    commit_before_recovery = {}
    commit_before_recovery_tps = 0
    for time, batch_id, block in blocks_two[0]:
        if time < start[0]:
            commit_before_recovery[batch_id] = time
            commit_before_recovery_tps += (sizes_two[batch_id]/512)
    print("Transactions before recovery: {}".format(commit_before_recovery_tps/(start[0]-min_time)));
    print(end_to_end_latency(commit_before_recovery, sent_samples, received_samples)*1000)
 
    commit_before_recovery = {}
    for time, batch_id, block in blocks_two[0]:
        if time > start[0] and time < start[1]:
            commit_before_recovery[batch_id] = time
    print(end_to_end_latency(commit_before_recovery, sent_samples, received_samples)*1000)


    commit_before_recovery = {}
    commit_before_recovery_tps = 0
    for time, batch_id, block in blocks_two[0]:
        if time > (1721961656.542):
            commit_before_recovery[batch_id] = time
            commit_before_recovery_tps += (sizes_two[batch_id]/512)
    print("Time: {}".format(152+min_time))
    print("Transactions before recovery: {}".format(commit_before_recovery_tps/(300-(end[0]-min_time))));
    print(end_to_end_latency(commit_before_recovery, sent_samples, received_samples)*1000)

    print('\n\n')
    print(end[0]-start[0])
    return
main()
