# SC-4 Information in Shared System Resources

- Control: SC-4
- Familia: SC — Protección de sistemas y comunicaciones
- Función CSF 2.0: PR (Proteger)
- Fuente: NIST SP 800-53 5.2.0

## Control

Prevent unauthorized and unintended information transfer via shared system resources.

## Guía complementaria

Preventing unauthorized and unintended information transfer via shared system resources stops information produced by the actions of prior users or roles (or the actions of processes acting on behalf of prior users or roles) from being available to current users or roles (or current processes acting on behalf of current users or roles) that obtain access to shared system resources after those resources have been released back to the system. Information in shared system resources also applies to encrypted representations of information. In other contexts, control of information in shared system resources is referred to as object reuse and residual information protection. Information in shared system resources does not address information remanence, which refers to the residual representation of data that has been nominally deleted; covert channels (including storage and timing channels), where shared system resources are manipulated to violate information flow restrictions; or components within systems for which there are only single users or roles.
