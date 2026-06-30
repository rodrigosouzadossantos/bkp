use reqwest::blocking::Client;

pub struct LakeFSClient { pub endpoint: String, pub repo: String }

impl LakeFSClient {
  pub fn commit(&self, branch: &str, message: &str) {
    let client = Client::new();
    let _ = client.post(format!("{}/api/v1/commits", self.endpoint))
      .json(&serde_json::json!({ "repo": self.repo, "branch": branch, "message": message }))
      .send();
  }
}
