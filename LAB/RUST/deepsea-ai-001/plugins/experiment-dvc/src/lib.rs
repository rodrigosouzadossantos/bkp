pub fn dvc_add_commit(path: &str) {
  std::process::Command::new("dvc").arg("add").arg(path).output().unwrap();
  std::process::Command::new("dvc").arg("commit").arg("-m").arg("Add data").arg(path).output().unwrap();
}
