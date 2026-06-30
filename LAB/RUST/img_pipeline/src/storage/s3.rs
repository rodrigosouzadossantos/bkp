use crate::storage::{ImageId, Storage};

use anyhow::Result;
use async_trait::async_trait;
use aws_sdk_s3::{types::CommonPrefix, Client};
use bytes::Bytes;
use futures::{Stream, StreamExt};
use std::{
  collections::VecDeque,
  pin::Pin,
};

#[derive(Clone)]
pub struct S3Storage {
  pub client: Client,
  pub bucket: String,
}

const MAX_KEYS: i32 = 1000;

async fn expand_prefix(
  client: &Client,
  bucket: &str,
  prefix: &str,
) -> Result<(Vec<String>, bool)> {
  let resp = client
    .list_objects_v2()
    .bucket(bucket)
    .prefix(prefix)
    .delimiter("/")
    .max_keys(MAX_KEYS)
    .send()
    .await?;
  let sub_prefixes = resp
    .common_prefixes
    .unwrap_or_default()
    .into_iter()
    .filter_map(|p: CommonPrefix| p.prefix)
    .collect::<Vec<_>>();
  let is_leaf = sub_prefixes.is_empty();
  Ok((sub_prefixes, is_leaf))
}

/// Sequential listing for a leaf prefix
fn list_sequential(
  client: Client,
  bucket: String,
  prefix: String,
) -> impl Stream<Item = Result<ImageId>> + Send {
  async_stream::try_stream! {
    let mut continuation = None;
    loop {
      let mut req = client
        .list_objects_v2()
        .bucket(&bucket)
        .prefix(&prefix)
        .max_keys(MAX_KEYS);
      if let Some(token) = continuation {
        req = req.continuation_token(token);
      }
      let resp = req.send().await?;
      if let Some(contents) = resp.contents {
        for obj in contents {
          if let Some(key) = obj.key {
            yield key;
          }
        }
      }
      if resp.is_truncated.unwrap_or(false) {
        continuation = resp.next_continuation_token;
      } else {
        break;
      }
    }
  }
}

#[async_trait]
impl Storage for S3Storage {
  async fn list(
    &self,
    prefix: &str,
  ) -> Result<Pin<Box<dyn Stream<Item = Result<ImageId>> + Send>>> {
    let client = self.client.clone();
    let bucket = self.bucket.clone();

    let initial = VecDeque::from([prefix.to_string()]);
    let stream = futures::stream::unfold(initial, move |mut queue| {
      let client = client.clone();
      let bucket = bucket.clone();
      async move {
        let prefix = queue.pop_front()?;
        match expand_prefix(&client, &bucket, &prefix).await {
          Ok((subs, is_leaf)) => {
            if is_leaf {
              let s = list_sequential(
                client.clone(),
                bucket.clone(),
                prefix,
              );

              let boxed: Pin<Box<dyn Stream<Item = Result<ImageId>> + Send>> =
                Box::pin(s);

              Some((boxed, queue))
            } else {
              for p in subs {
                queue.push_back(p);
              }

              let empty: Pin<Box<dyn Stream<Item = Result<ImageId>> + Send>> =
                Box::pin(futures::stream::empty());

              Some((empty, queue))
            }
          }
          Err(e) => {
            let err_stream: Pin<Box<dyn Stream<Item = Result<ImageId>> + Send>> =
              Box::pin(futures::stream::iter(vec![Err(e)]));

            Some((err_stream, queue))
          }
        }
      }
    })
    .flatten();
    Ok(Box::pin(stream))
  }

  async fn read(&self, id: &ImageId) -> Result<Bytes> {
    let obj = self.client
      .get_object()
      .bucket(&self.bucket)
      .key(id)
      .send()
      .await?;
    let data = obj.body.collect().await?;
    Ok(data.into_bytes())
  }

  async fn read_stream(
    &self,
    id: &ImageId,
  ) -> Result<Pin<Box<dyn Stream<Item = Result<Bytes>> + Send>>> {
    let obj = self.client
      .get_object()
      .bucket(&self.bucket)
      .key(id)
      .send()
      .await?;
    let bytes = obj.body.collect().await?.into_bytes();
    Ok(Box::pin(futures::stream::once(async move { Ok(bytes) })))
  }
}
