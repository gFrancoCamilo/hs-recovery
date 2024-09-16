use crate::config::Committee;
use crate::consensus::ConsensusMessage;
use crate::messages::{Block, Blocks, FirstBlocks, QC};
use crate::core::{MY_TIP};
use bytes::Bytes;
use crypto::{Digest, PublicKey};
use log::warn;
use network::ReliableSender;
use store::Store;
use tokio::sync::mpsc::Receiver;
use std::net::SocketAddr;
use std::collections::HashMap;

#[cfg(test)]
#[path = "tests/helper_tests.rs"]
pub mod helper_tests;

/// A task dedicated to help other authorities by replying to their sync requests.
pub struct NewHelper {
    name: PublicKey,
    /// The committee information.
    committee: Committee,
    /// The persistent storage.
    store: Store,
    /// Input channel to receive sync requests.
    rx_requests: Receiver<(Digest, u64, PublicKey)>,
    /// A network sender to reply to the sync requests.
    network: ReliableSender,
}

impl NewHelper {
    pub fn spawn(name: PublicKey, committee: Committee, store: Store, rx_requests: Receiver<(Digest, u64, PublicKey)>, firewall: HashMap<u64,Vec<SocketAddr>>, allow_communications_at_round: u64, network_delay: u64, dns: HashMap<SocketAddr, SocketAddr>) {
        tokio::spawn(async move {
            Self {
                name,
                committee,
                store,
                rx_requests,
                network: ReliableSender::new(firewall, allow_communications_at_round, network_delay, dns),
            }
            .run()
            .await;
        });
    }

    async fn run(&mut self) {
        let mut i = 0;
        let mut block = Block::default();
        let mut parent;
        let mut vec_blocks = Vec::new();
        let mut round = 0;
        while let Some((digest, num_blocks, origin)) = self.rx_requests.recv().await {
            // TODO [issue #58]: Do some accounting to prevent bad nodes from monopolizing our resources.

            // get the requestors address.
            let address = match self.committee.address(&origin) {
                Some(x) => x,
                None => {
                    warn!("Received sync request from unknown authority: {}", origin);
                    continue;
                }
            };

            parent = digest;
            warn!("Received new sync request for {:?} blocks, starting from {:?}. Current value of i is {}", num_blocks, parent.clone(), i);

            while i < num_blocks {
                // Reply to the request (if we can).
                if let Some(bytes) = self
                    .store
                    .read(parent.to_vec())
                    .await
                    .expect("Failed to read from storage")
                {
                    block =
                        bincode::deserialize(&bytes).expect("Failed to deserialize our own block");
                    warn!("Block here is {:?} BBBBBBBBBBBBB", block);
                    vec_blocks.push(block.clone());
                    //let message = bincode::serialize(&ConsensusMessage::Propose(block.clone()))
                    //    .expect("Failed to serialize block");
                } else {
                    let mut last_block;
                    {
                        let my_mutex = MY_TIP.lock().unwrap();
                        warn!("MY TIP here is {:?} CCCCCCCCCCCCCCC", *my_mutex);
                        last_block = my_mutex.clone();
                    }
                    let bytes = self.store.read(last_block.to_vec()).await.unwrap().expect("Failed to read last block");
                    block = 
                        bincode::deserialize(&bytes).expect("Failed to deserialize our own block");
                    warn!("Block here is {:?} CCCCCCCCCCCCCCC", block);
                    vec_blocks.push(block.clone());
                }
                if i == 0 {
                    round = block.round.clone();
                }
                if block.qc == QC::genesis() {
                    vec_blocks.push(Block::genesis());
                    i = num_blocks;
                } else {
                    parent = block.clone().parent().clone();
                }
                i = i + 1;
            }
            //let message = bincode::serialize(&vec_blocks).expect("Failed to serialize vector of blocks");
                        
            if vec_blocks.is_empty() == false {
                let message;
                if num_blocks == 10 {
                    let values: Vec<_> = self.committee.authorities.values().cloned().collect();
                    let my_authorities: Vec<_> = values.iter().filter(|x| !self.network.firewall.get(&(round/self.network.allow_communications_at_round)).unwrap_or(&self.network.firewall[&((self.network.firewall.len()-1) as u64)]).contains(&x.address) && x.address != self.committee.address(&self.name).unwrap()).collect();
                    let my_clique: Vec<_> = my_authorities.iter().map(|x| x.address).collect();
                    message = bincode::serialize(&ConsensusMessage::FirstBlocks(Blocks::new(self.name, vec_blocks.clone()), my_clique.clone())).expect("Failed to serialize vec of blocks");
                } else {
                    message = bincode::serialize(&ConsensusMessage::Blocks(Blocks::new(self.name, vec_blocks.clone()))).expect("Failed to serialize vec of blocks");
                }
                warn!("Vec blocks is {:?}", vec_blocks);
                let handler = self.network.send(address, Bytes::from(message)).await;
                let _ = handler.await;
            }
            i = 0;
            vec_blocks = Vec::new();
        }
    }
}
