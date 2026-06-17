# Limitations

## Public data only

This project uses public REST endpoints. It does not access private accounts, private orderflow, exchange matching engines, wallet data or broker APIs.

## Exchange coverage

A composite artifact can be incomplete if one or more venues fail or if a symbol is not listed on a venue.

## Snapshot orderbook proxy

The composite orderbook ladder aggregates public snapshots into buckets. It is not equivalent to a consolidated full-depth book and should not be interpreted as proof of hidden liquidity.

## No trading semantics

The project intentionally avoids trading signals, execution instructions, stop-loss/take-profit logic, position sizing and performance claims.
