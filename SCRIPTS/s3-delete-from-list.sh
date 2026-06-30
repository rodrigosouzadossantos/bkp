cat list.txt | xargs -n 1000 -P 8 bash -c '
  keys=$(printf "{\"Key\":\"%s\"}," "$@")
  aws s3api delete-objects --bucket YOUR_BUCKET_NAME --delete "{\"Objects\":[${keys%,}],\"Quiet\":true}"
' _ >> delete_log.txt 2>&1
