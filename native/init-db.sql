\set ON_ERROR_STOP on
SELECT 'CREATE ROLE traveler_lab2 LOGIN PASSWORD ''traveler_lab2_dev'''
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='traveler_lab2') \gexec
SELECT 'CREATE DATABASE traveler_lab2 OWNER traveler_lab2'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='traveler_lab2') \gexec
