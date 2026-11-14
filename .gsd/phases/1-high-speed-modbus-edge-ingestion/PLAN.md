---
phase: 1
name: High-Speed Modbus TCP Edge Ingestion
status: complete
created: 2026-10-12T00:00:00Z
updated: 2026-11-14T15:00:00Z
---

# Plan 1: High-Speed Modbus TCP Edge Ingestion

## Objective
Deterministic signal acquisition from Selec MiBRX-6M PLC with register decoding and timestamping.

## Tasks
- [x] Plan 1.1: Register mapping parser and block optimization
- [x] Plan 1.2: Asynchronous multi-rhythm polling loops

## Must-Haves
- [x] PyModbus 3.6 async Modbus TCP client with 3-tier polling
- [x] Register map validation and integer-to-engineering conversion

---

*Last updated: 2026-11-14*
