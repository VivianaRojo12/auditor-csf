# AU-7 Audit Record Reduction and Report Generation

- Control: AU-7
- Familia: AU — Auditoría y rendición de cuentas
- Función CSF 2.0: DE (Detectar)
- Fuente: NIST SP 800-53 5.2.0

## Control

Provide and implement an audit record reduction and report generation capability that:
  - a. Supports on-demand audit record review, analysis, and reporting requirements and after-the-fact investigations of incidents; and
  - b. Does not alter the original content or time ordering of audit records.

## Guía complementaria

Audit record reduction is a process that manipulates collected audit log information and organizes it into a summary format that is more meaningful to analysts. Audit record reduction and report generation capabilities do not always emanate from the same system or from the same organizational entities that conduct audit logging activities. The audit record reduction capability includes modern data mining techniques with advanced data filters to identify anomalous behavior in audit records. The report generation capability provided by the system can generate customizable reports. Time ordering of audit records can be an issue if the granularity of the timestamp in the record is insufficient.
