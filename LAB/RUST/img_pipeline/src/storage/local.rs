use super::*;
use futures::{
  stream,
  StreamExt,
};
use memmap2::Mmap;
use std::{
  fs::File,
  path::PathBuf,
};
use tokio::fs::DirEntry;
use bytes::Bytes;

pub struct LocalFs {
    root: PathBuf,
}

impl LocalFs {
    pub fn new(root: PathBuf) -> Self {
        Self { root }
    }
}

#[async_trait::async_trait]
impl Storage for LocalFs {
    async fn list(
        &self,
        prefix: &str,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ImageId>> + Send>>> {
        let root = self.root.join(prefix);
        let entries = tokio::fs::read_dir(root).await?;

        let stream = tokio_stream::wrappers::ReadDirStream::new(entries)
            .filter_map(|e: Result<DirEntry, std::io::Error>| async move {
                match e {
                    Ok(entry) => {
                        let path = entry.path();
                        if path.is_file() {
                            Some(Ok(path.to_string_lossy().to_string()))
                        } else {
                            None
                        }
                    }
                    Err(e) => Some(Err(e.into())),
                }
            });

        Ok(Box::pin(stream))
    }

    async fn read(&self, id: &ImageId) -> Result<Bytes> {
        let data = tokio::fs::read(id).await?;
        Ok(Bytes::from(data))
    }

    async fn read_stream(
        &self,
        id: &ImageId,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<Bytes>> + Send>>> {
        let file = File::open(id)?;
        let mmap = unsafe { Mmap::map(&file)? };

        let bytes = Bytes::from_owner(mmap);

        Ok(Box::pin(stream::once(async move { Ok(bytes) })))
    }
}
