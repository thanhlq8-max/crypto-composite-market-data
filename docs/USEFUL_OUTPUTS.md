# Useful outputs for developers and researchers

This project is valuable when it helps users answer data-quality and market-data questions that are otherwise tedious to reproduce.

## Questions the artifacts can answer

### Venue coverage

- Which requested venues returned usable OHLCV data?
- Which venues returned orderbook snapshots?
- Which market types are missing funding or open-interest context?

### Composite price quality

- Did multiple venues agree on the latest close?
- Was latest timestamp coverage complete, partial, or weak?
- Is cross-venue price dispersion high enough to downgrade confidence in the artifact?

### Public depth structure

- Where is visible public quote depth concentrated near the reference price?
- Is depth concentrated on one venue or distributed across venues?
- Is the ladder based on enough venues to be treated as a composite artifact?

### Multi-symbol monitoring

- Which assets produced complete artifacts?
- Which assets failed due to listing gaps or public endpoint errors?
- Which symbols need connector fixes before analysis?

## What users should not infer

The artifacts do not identify hidden liquidity, private orderflow, dealer inventory, retail positioning, or profitable trading opportunities. They are public-data diagnostics and reproducible data artifacts.
