"""Pluggable storage backends behind app/store.py.

Each subsystem (vectors / registry / object storage) has a local file-based
backend (used in dev) and a managed-cloud backend (used in production), selected
by config in app/store.py. Cloud SDKs are imported lazily so a local install
never needs qdrant-client / psycopg / boto3.
"""
