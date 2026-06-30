use bytes::Bytes;

pub struct ImageView {
    pub data: Vec<u8>,
}

pub async fn decode(bytes: Bytes) -> ImageView {
    tokio::task::spawn_blocking(move || {
        ImageView { data: bytes.to_vec() }
    })
    .await
    .unwrap()
}
