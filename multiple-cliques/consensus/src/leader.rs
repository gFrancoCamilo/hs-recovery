use crate::config::{Committee};
use crate::consensus::Round;
use crypto::PublicKey;
use std::net::{SocketAddr};
use log::info;
use std::collections::HashMap;

pub type LeaderElector = RRLeaderElector;

pub struct RRLeaderElector {
    committee: Committee,
    //pub firewall: Vec<SocketAddr>,
}

impl RRLeaderElector {
    pub fn new(committee: Committee) -> Self {
        Self { committee }
    }
    /*pub fn get_leader(&self, round: Round, firewall: Vec<SocketAddr>) -> PublicKey {
        let mut keys: Vec<_> = self.committee.authorities.keys().cloned().collect();
        keys.sort();
        keys[round as usize % self.committee.size()]
    }*/
    pub fn get_leader(&self, round: Round, firewall: Vec<SocketAddr>, dns: HashMap<SocketAddr, SocketAddr>) -> PublicKey {
        let mut keys: Vec<_> = self.committee.authorities.keys().cloned().collect();
        let values: Vec<_> = self.committee.authorities.values().cloned().collect();
        let mut addresses: Vec<_> = values.iter().map(|x| dns[&x.address]).collect();
        addresses.sort();
        let mut keys_order = Vec::new();

        for address in addresses.iter(){
            for key in keys.iter() {
                if dns[&self.committee.address(&key).unwrap()] == *address {
                    keys_order.push(key.clone());
                }
            }
        }
        
        let mut indices = Vec::new(); 
        info!("Firewall is {:?}", firewall);
        //info!("Adresses are {:?}", addresses.clone());
        //info!("Keys are {:?}", keys_order.clone());
        //TODO:Optimize this code

        //let mut counter = 0;
        //for add in firewall.iter(){
        //    if add.to_string().find(':').map(|i| add.to_string()[i+1..].parse().ok()).flatten() < Some((self.committee.faults) + 9000 + 1){
        //        counter += 1;
        //    }
        //}
        //let mut virtual_address;
        for _value in addresses.iter() {
            //virtual_address = dns[&_value];
            if firewall.contains(&_value){
                indices.push(false);
            }else{
                indices.push(true);
            }
        }
        //Get the indices of values in firewall to retain
        //indices = values.into_iter().map(|x| {if firewall.contains(&x.address){ false } else { true }}).collect();
        let mut iter = indices.iter();
        keys_order.retain(|_| *iter.next().unwrap());
        //keys_order.sort();
        for key in keys_order.iter(){
            info!("Keys after removal: {}", key);
        }

        info!("Computing committee size with firewall: {:?}", self.committee.size_by_firewall(firewall.clone()));

        info!("Elected leader in round {} is {}", round, keys_order[round as usize % (self.committee.size_by_firewall(firewall.clone()))]); //- 1)]);
        keys_order[round as usize % (self.committee.size_by_firewall(firewall))]// - 1)]
    }
}
