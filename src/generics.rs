// Copyright (c) Mike Nye, Fred Clausen
//
// Licensed under the MIT license: https://opensource.org/licenses/MIT
// Permission is granted to use, copy, modify, and redistribute the work.
// Full license information available in the project LICENSE file.
//
use derive_getters::Getters;
use serde_json::Value;
use std::collections::HashMap;
use std::net::SocketAddr;
use std::time::Duration;
use stubborn_io::ReconnectOptions;
use tokio::sync::mpsc;
use tokio::sync::mpsc::Receiver;

/// Shorthand for the transmit half of the message channel.
pub type Tx = mpsc::UnboundedSender<String>;

/// Shorthand for the receive half of the message channel.
pub type Rx = mpsc::UnboundedReceiver<String>;

pub type DurationIterator = Box<dyn Iterator<Item = Duration> + Send + Sync>;

pub struct SenderServer<T> {
    pub host: String,
    pub proto_name: String,
    pub socket: T,
    pub channel: Receiver<Value>,
}

pub struct Shared {
    pub peers: HashMap<SocketAddr, Tx>,
}

#[derive(Getters, Clone)]
pub struct SenderServerConfig {
    pub send_udp: Vec<String>,
    pub send_tcp: Vec<String>,
    pub serve_tcp: Vec<String>,
    pub serve_zmq: Vec<String>,
    pub max_udp_packet_size: usize,
}

#[derive(Getters, Clone)]
pub struct OutputServerConfig {
    pub listen_udp: Vec<String>,
    pub listen_tcp: Vec<String>,
    pub receive_tcp: Vec<String>,
    pub receive_zmq: Vec<String>,
    pub reassembly_window: u64,
}

// create ReconnectOptions. We want the TCP stuff that goes out and connects to clients
// to attempt to reconnect
// See: https://docs.rs/stubborn-io/latest/src/stubborn_io/config.rs.html#93

pub fn reconnect_options() -> ReconnectOptions {
    ReconnectOptions::new()
        .with_exit_if_first_connect_fails(false)
        .with_retries_generator(get_our_standard_reconnect_strategy)
}

fn get_our_standard_reconnect_strategy() -> DurationIterator {
    let initial_attempts = vec![
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(5),
        Duration::from_secs(10),
        Duration::from_secs(20),
        Duration::from_secs(30),
        Duration::from_secs(40),
        Duration::from_secs(50),
        Duration::from_secs(60),
    ];

    let repeat = std::iter::repeat(Duration::from_secs(60));

    let forever_iterator = initial_attempts.into_iter().chain(repeat);

    Box::new(forever_iterator)
}
