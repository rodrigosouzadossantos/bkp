use reqwest::blocking::Client;

pub struct MLFlowTracker { pub endpoint: String }

impl MLFlowTracker {
  pub fn start_run(&self, run_name: &str) {
    let client = Client::new();
    let _ = client.post(format!("{}/api/2.0/mlflow/runs/create", self.endpoint))
      .json(&serde_json::json!({ "run_name": run_name }))
      .send();
  }
}
