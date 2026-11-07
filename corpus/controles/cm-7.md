# CM-7 Least Functionality

- Control: CM-7
- Familia: CM — Gestión de la configuración
- Función CSF 2.0: ID (Identificar)
- Fuente: NIST SP 800-53 5.2.0

## Control

  - a. Configure the system to provide only [mission-essential capabilities] ; and
  - b. Prohibit or restrict the use of the following functions, ports, protocols, software, and/or services: [organization-defined prohibited or restricted functions, system ports, protocols, software, and/or services].

## Guía complementaria

Systems provide a wide variety of functions and services. Some of the functions and services routinely provided by default may not be necessary to support essential organizational missions, functions, or operations. Additionally, it is sometimes convenient to provide multiple services from a single system component, but doing so increases risk over limiting the services provided by that single component. Where feasible, organizations limit component functionality to a single function per component. Organizations consider removing unused or unnecessary software and disabling unused or unnecessary physical and logical ports and protocols to prevent unauthorized connection of components, transfer of information, and tunneling. Organizations employ network scanning tools, intrusion detection and prevention systems, and end-point protection technologies, such as firewalls and host-based intrusion detection systems, to identify and prevent the use of prohibited functions, protocols, ports, and services. Least functionality can also be achieved as part of the fundamental design and development of the system (see [SA-8](#sa-8), [SC-2](#sc-2) , and [SC-3](#sc-3)).
