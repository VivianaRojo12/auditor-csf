# AU-5 Response to Audit Logging Process Failures

- Control: AU-5
- Familia: AU — Auditoría y rendición de cuentas
- Función CSF 2.0: DE (Detectar)
- Fuente: NIST SP 800-53 5.2.0

## Control

  - a. Alert [personnel or roles] within [time period] in the event of an audit logging process failure; and
  - b. Take the following additional actions: [additional actions].

## Guía complementaria

Audit logging process failures include software and hardware errors, failures in audit log capturing mechanisms, and reaching or exceeding audit log storage capacity. Organization-defined actions include overwriting oldest audit records, shutting down the system, and stopping the generation of audit records. Organizations may choose to define additional actions for audit logging process failures based on the type of failure, the location of the failure, the severity of the failure, or a combination of such factors. When the audit logging process failure is related to storage, the response is carried out for the audit log storage repository (i.e., the distinct system component where the audit logs are stored), the system on which the audit logs reside, the total audit log storage capacity of the organization (i.e., all audit log storage repositories combined), or all three. Organizations may decide to take no additional actions after alerting designated roles or personnel.
