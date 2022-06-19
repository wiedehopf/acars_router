// Copyright (c) Mike Nye, Fred Clausen
//
// Licensed under the MIT license: https://opensource.org/licenses/MIT
// Permission is granted to use, copy, modify, and redistribute the work.
// Full license information available in the project LICENSE file.
//

use crate::helper_functions::strip_line_endings;
use log::{debug, error, trace};
use stubborn_io::StubbornTcpStream;
use tokio::sync::mpsc::Sender;
use tokio_stream::StreamExt;
use tokio_util::codec::{Framed, LinesCodec};

pub struct TCPReceiverServer {
    pub host: String,
    pub proto_name: String,
}

impl TCPReceiverServer {
    pub async fn run(self, channel: Sender<serde_json::Value>) {
        let TCPReceiverServer { host, proto_name } = self;
        trace!("[TCP Receiver Server {}] Starting", proto_name);

        let stream = StubbornTcpStream::connect(host.clone()).await.unwrap();

        // create a buffered reader and send the messages to the channel

        let reader = tokio::io::BufReader::new(stream);
        let mut lines = Framed::new(reader, LinesCodec::new());

        while let Some(Ok(line)) = lines.next().await {
            // Clean up the line endings. This is probably unnecessary but it's here for safety.
            let stripped = strip_line_endings(&line).to_owned();

            match serde_json::from_str::<serde_json::Value>(stripped.as_str()) {
                Ok(msg) => {
                    trace!("[TCP SERVER: {}]: {}", proto_name, msg);
                    match channel.send(msg).await {
                        Ok(_) => debug!("Message sent to channel"),
                        Err(e) => error!("Error sending message to channel: {}", e),
                    };
                }
                Err(e) => error!("{}", e),
            }
        }
    }
}
