# Postgres Exposure Check Action

Checks a list of Postgres hosts to ensure they are **not** exposed to the public internet.

## Usage

```yaml
- name: Check for exposed Postgres servers
  uses: stjudd109/postgres-exposure-check-action@v1
  with:
    postgres_hosts: 'db1.example.com,db2.example.com,10.0.0.5'
    redshift_hosts: 'db2.example.com'
    postgres_port: '5432'
    redshift_port: '5439'
    timeout: '5'
    sslmode: 'prefer'
    webhook_url: ${{ secrets.RESULTS_WEBHOOK_URL }}   # Optional
- name: Upload JSON report
    uses: actions/upload-artifact@v4
    with:
    name: postgres-report-json
    path: postgres_access_results.json
- name: Upload Markdown summary
    uses: actions/upload-artifact@v4
    with:
    name: postgres-report-markdown
    path: postgres_check_summary.md
```
