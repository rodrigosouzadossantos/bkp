use reqwest::blocking::Client;

pub struct WandBTracker { pub project: String, pub entity: String }

impl WandBTracker {
  pub fn log_metric(&self, key: &str, value: f64) {
    let client = Client::new();
    let _ = client.post("https://api.wandb.ai/metrics")
      .json(&serde_json::json!({ "project": self.project, "entity": self.entity, "key": key, "value": value }))
      .send();
  }
}
