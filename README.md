# matrix_mastodon_gateway

Tiny Matrix to Mastodon gateway written in Python.

Drop something into a configurable room on your Synapse instance (or anything that can talk to a Matrix client) and watch it appear on your favourite
social netwok. This code is meant to be a PoC rather than a production-quality implementation, so for example, the error checking and validation aspects
have been kept to a minimum.

Requires PyPi matrix_client and Mastodon.py in addition to existing access tokens for both APIs (cf. the corresponding module documentation). 

Drop it into a cron job or systemd timer for regular execution.
