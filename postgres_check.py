import os
import json
import requests
import socket
from psycopg2 import connect, OperationalError
from tabulate import tabulate


def parse_hosts(hosts_string):
    """
    Parse a comma-separated list of hosts into a list of hostnames or IPs.
    """
    return [h.strip() for h in hosts_string.split(",") if h.strip()]


def check_sql_exposure(host, port, db_type, timeout=5, sslmode="prefer"):
    """
    Check if a SQL server is exposed to the public internet.
    """
    BAD_USER = "notarealuser"
    BAD_PASS = "notarealpass"
    dbname = "dev" if db_type == "redshift" else "postgres"
    result = {
        "type": db_type,
        "host": host,
        "port": port,
        "exposed": False,
        "status": "",
        "error": "",
    }
    try:
        conn = connect(
            dbname=dbname,
            user=BAD_USER,
            password=BAD_PASS,
            host=host,
            port=port,
            connect_timeout=timeout,
            sslmode=sslmode,
        )
        conn.close()
        result["status"] = "?? Unexpectedly connected"
    except OperationalError as e:
        msg = str(e).lower()
        if (
            "authentication failed" in msg
            or "password authentication failed" in msg
            or "no password supplied" in msg
            or "scram channel binding check failed" in msg
        ):
            result["exposed"] = True
            result["status"] = "Auth failed (DB EXPOSED)"
        elif (
            "could not connect to server" in msg
            or "connection refused" in msg
            or "network is unreachable" in msg
            or "timeout expired" in msg
            or "timed out" in msg
            or "name or service not known" in msg
            or "ssl syscall error: eof detected" in msg
            or "server closed the connection unexpectedly" in msg
        ):
            result["exposed"] = False
            result["status"] = "Not exposed (host unreachable)"
        else:
            result["status"] = "Other error"
            result["error"] = msg
    except socket.timeout:
        result["status"] = "Timeout (Not exposed)"
    except Exception as e:
        result["status"] = "Other error"
        result["error"] = str(e)
    return result


def main():
    """
    Main function to check SQL exposure.
    """
    postgres_hosts = os.getenv("POSTGRES_HOSTS", "")
    redshift_hosts = os.getenv("REDSHIFT_HOSTS", "")
    postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
    redshift_port = int(os.getenv("REDSHIFT_PORT", "5439"))
    timeout = int(os.getenv("SQL_TIMEOUT", "5"))
    sslmode = os.getenv("SQL_SSLMODE", "prefer")
    webhook_url = os.getenv("RESULTS_WEBHOOK_URL", "")
    hosts_json_file = os.getenv("HOSTS_JSON_FILE", "")

    # Check if JSON file is provided and read hosts from it if available
    if hosts_json_file and os.path.exists(hosts_json_file):
        try:
            with open(hosts_json_file, 'r') as f:
                hosts_data = json.load(f)
            
            # If JSON file has postgres_hosts, use those
            if "postgres_hosts" in hosts_data and isinstance(hosts_data["postgres_hosts"], list):
                postgres_hosts = ','.join(hosts_data["postgres_hosts"])
            
            # If JSON file has redshift_hosts, use those
            if "redshift_hosts" in hosts_data and isinstance(hosts_data["redshift_hosts"], list):
                redshift_hosts = ','.join(hosts_data["redshift_hosts"])
                
            print(f"Loaded hosts from JSON file: {hosts_json_file}")
        except Exception as e:
            print(f"Error reading hosts JSON file: {str(e)}")

    results = []

    if postgres_hosts:
        for host in parse_hosts(postgres_hosts):
            results.append(check_sql_exposure(
                host, postgres_port, "postgres", timeout, sslmode))
    if redshift_hosts:
        for host in parse_hosts(redshift_hosts):
            results.append(check_sql_exposure(
                host, redshift_port, "redshift", timeout, sslmode))

    headers = ["Type", "Host", "Port", "Exposed?", "Status", "Error"]
    table = [
        [
            r["type"],
            r["host"],
            r["port"],
            ":red_circle:" if r["exposed"] else ":white_check_mark:",
            r["status"],
            r["error"],
        ]
        for r in results
    ]
    markdown_table = tabulate(table, headers, tablefmt="github")

    if len(results) == 0:
        print("No results found")
        summary_md = """### SQL Exposure Scan (Postgres/Redshift)\n\nNo results found.  This is good!"""
    else:
        summary_md = f"""### SQL Exposure Scan (Postgres/Redshift)\n\n{markdown_table}\n"""

    # Write summary if in GitHub Actions, otherwise save locally
    gha_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gha_summary:
        with open(gha_summary, "a") as summary:
            summary.write(summary_md)
    else:
        print(summary_md)
        with open("sql_check_summary.md", "w") as f:
            f.write(summary_md)

    with open("sql_access_results.json", "w") as f:
        json.dump(results, f, indent=2)
    if webhook_url:
        try:
            r = requests.post(webhook_url, json=results, timeout=10)
            print(f"Webhook response: {r.status_code}")
        except Exception as e:
            print(f"Webhook failed: {str(e)}")


if __name__ == "__main__":
    main()
