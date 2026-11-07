# IA-9 Service Identification and Authentication

- Control: IA-9
- Familia: IA — Identificación y autenticación
- Función CSF 2.0: PR (Proteger)
- Fuente: NIST SP 800-53 5.2.0

## Control

Uniquely identify and authenticate [system services and applications] before establishing communications with devices, users, or other services or applications.

## Guía complementaria

Services that may require identification and authentication include web applications using digital certificates or services or applications that query a database. Identification and authentication methods for system services and applications include information or code signing, provenance graphs, and electronic signatures that indicate the sources of services. Decisions regarding the validity of identification and authentication claims can be made by services separate from the services acting on those decisions. This can occur in distributed system architectures. In such situations, the identification and authentication decisions (instead of actual identifiers and authentication data) are provided to the services that need to act on those decisions.
