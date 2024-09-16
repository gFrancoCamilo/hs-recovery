use crypto::PublicKey;
use log::info;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::convert::TryFrom;

pub type Stake = u32;
pub type EpochNumber = u128;

#[derive(Serialize, Deserialize)]
pub struct Parameters {
    pub timeout_delay: u64,
    pub sync_retry_delay: u64,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct NetworkParameters {
    pub firewall: HashMap<u64, Vec<String>>,
    //pub new_firewall: Vec<String>,
    pub allow_communications_at_round: u64,
    pub network_delay: u64,
    pub dns: HashMap<u64, String>,
}

impl Default for NetworkParameters {
    fn default() -> Self{
        Self {
            firewall: HashMap::new(),
            //new_firewall: Vec::new(),
            allow_communications_at_round: 20000,
            network_delay: 10,
            dns: HashMap::new(),
        }
    }
}

impl NetworkParameters {
    pub fn log(&self) {
        info!("Network firewall set: {:?}", self.firewall);
        info!("Firewall will be changed at round {}", self.allow_communications_at_round);
    }
}

impl Default for Parameters {
    fn default() -> Self {
        Self {
            timeout_delay: 5_000,
            sync_retry_delay: 10_000,
        }
    }
}

impl Parameters {
    pub fn log(&self) {
        // NOTE: These log entries are used to compute performance.
        info!("Timeout delay set to {} rounds", self.timeout_delay);
        info!("Sync retry delay set to {} ms", self.sync_retry_delay);
    }
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Authority {
    pub stake: Stake,
    pub address: SocketAddr,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Committee {
    pub authorities: HashMap<PublicKey, Authority>,
    pub epoch: EpochNumber,
    pub num_of_twins: u32,
    pub faults: u32,
}

impl Committee {
    pub fn new(info: Vec<(PublicKey, Stake, SocketAddr)>, epoch: EpochNumber, num_of_twins: u32, faults: u32) -> Self {
        Self {
            authorities: info
                .into_iter()
                .map(|(name, stake, address)| {
                    let authority = Authority { stake, address };
                    (name, authority)
                })
                .collect(),
            epoch,
            num_of_twins,
            faults,
        }
    }

    pub fn size(&self) -> usize {
        //info!("Committe size set to {}", (self.authorities.len() - usize::try_from(self.num_of_twins).unwrap()));
        self.authorities.len() - usize::try_from(self.num_of_twins).unwrap()
        //self.authorities.len()
    }

    pub fn size_by_firewall(&self, firewall: Vec<SocketAddr>) -> usize {
        let mut counter = 0;
        let mut firewall_no_dup = firewall.clone();
        firewall_no_dup.dedup();
        self.authorities.len() - firewall_no_dup.len()
        //self.authorities.len()
    }
    pub fn stake(&self, name: &PublicKey) -> Stake {
        self.authorities.get(name).map_or_else(|| 0, |x| x.stake)
    }

    pub fn quorum_threshold(&self) -> Stake {
        // If N = 3f + 1 + k (0 <= k < 3)
        // then (2 N + 3) / 3 = 2f + 1 + (2k + 2)/3 = 2f + 1 + k = N - f
        let total_votes: Stake = self.authorities.values().map(|x| x.stake).sum();
        info!("Quorum threshold is {}", (2 * (total_votes-self.num_of_twins) / 3 + 1 ));
        2 * (total_votes-self.num_of_twins) / 3 + 1
        //2 * (total_votes) / 3 + 1
    }
    //
    pub fn quorum_threshold_firewall(&self, firewall: Vec<SocketAddr>) -> u32 {
        let size = self.size_by_firewall(firewall.clone());
        info!("Quorum threshold by firewall is {}", (2*(size as u32)/3 + 1));
        2 * (size as u32)/3 + 1
    }

    pub fn address(&self, name: &PublicKey) -> Option<SocketAddr> {
        self.authorities.get(name).map(|x| x.address)
    }

    pub fn broadcast_addresses(&self, myself: &PublicKey) -> Vec<(PublicKey, SocketAddr)> {
        self.authorities
            .iter()
            .filter(|(name, _)| name != &myself)
            .map(|(name, x)| (*name, x.address))
            .collect()
    }
    pub fn update_num_of_twins(&mut self, num_of_twins: u32) {
        self.num_of_twins = num_of_twins;
    }
}
