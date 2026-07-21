# nestHMS — OPD & Patient Registration (Odoo)

The **Outpatient Department** module of **nestHMS**, a complete Hospital Management System
built on Odoo and running in production in Tanzanian healthcare facilities. This module covers
the full outpatient journey — **Registration → Triage → Queue → Consultation → Vitals →
Diagnosis → Discharge** — with Tanzania-specific patient, insurance, and administrative data.

> Running in production. Built on **Odoo 18**. Licensed LGPL-3.
> This is the **root module** of the nestHMS suite — it installs standalone (depends only on
> core Odoo: `mail`, `hr`, `product`, `stock`).

---

## About nestHMS

nestHMS is a full hospital ERP built as a suite of integrated Odoo modules covering the entire
patient journey and hospital operations:

**Clinical:** OPD (this module) · IPD (wards & beds) · Theatre · Laboratory · Radiology ·
Pharmacy · Dental · Physiotherapy · Maternity · RCH · Emergency (EMD) · Ambulance · Mortuary
**Financial & support:** Billing · Insurance claims · shared Inventory framework

This repository publishes the **OPD & Patient Registration** module as an open-source work
sample. The wider suite is proprietary.

## What this module does

- 🧑‍⚕️ **Patient master record** — Tanzania-specific fields (NHIF/CHF numbers, 31-region
  administrative structure, next-of-kin), with paediatric and geriatric **auto-flagging**.
- 📝 **OPD visit lifecycle** — Registration → Triage → Queue → Consultation → Discharge, each
  stage tracked with timestamps.
- 🚦 **Triage** with 5-level colour coding (Red / Orange / Yellow / Green / Black) for acuity.
- ⏱️ **Digital patient queue** with wait-time tracking.
- ❤️ **Vital signs** capture per visit.
- 🩺 **ICD-10 diagnosis** recording from a preloaded code set.
- 💳 **Insurance & payer support** — NHIF, CHF, private schemes (Jubilee, AAR, Britam, …) and
  corporate self-insured, each with claims method, settlement days, and pre-authorization rules.
- 📦 **Department requisition & consumables** — OPD draws consumables from its own store
  location via a shared requisition sequence.
- 🧾 **Service catalogue** — consultations, procedures, and lab tests modelled as Odoo products
  so revenue routes cleanly into accounting.

## Technical highlights

- Clean **domain model** split across patient, visit, triage, queue, vitals, procedure, ICD-10,
  visit-type, insurance-scheme and requisition models.
- **Registration & visit-launcher wizards** that guide front-desk staff through a fast,
  validated intake flow.
- **Security groups & record rules** scoping access to clinical vs. front-desk vs.
  administrative roles.
- **Preloaded Tanzania reference data** — 31 regions, ICD-10 codes, national + private
  insurance schemes, visit types, and OPD service catalogue — so the module is usable on install.
- Designed with real **clinical domain knowledge** (the author's background is nursing), which
  is why the triage, acuity, and payer logic map to how hospitals actually operate.

## Repository structure

```
odoo_hms_opd/
├─ models/          # patient, visit, triage, queue, vitals, procedure, ICD-10, insurance…
├─ wizard/          # patient registration + visit launcher wizards
├─ views/           # forms, lists, queue board, menus
├─ security/        # groups, access rights, record rules
└─ data/            # regions, ICD-10, insurance schemes, services, sequences (Tanzania)
```

## Installation

1. Copy `odoo_hms_opd` into your Odoo addons path.
2. Update the apps list and install **nestHMS - OPD & Patient Registration**.
3. Open the **nestHMS / OPD** menu to register a patient and start a visit.

**Requires:** `mail`, `hr`, `product`, `stock` (core Odoo only).

## Screenshots

<!-- TODO: add screenshots — patient registration form, triage (colour acuity),
     the queue board, a visit/consultation form with vitals, and the insurance schemes. -->

---

## About

Built by **Albin Lema** — Odoo developer & ERP consultant, founder of CodeNest Tanzania, with a
clinical background (BSc Nursing). I build and deploy complete Odoo ERP systems in production —
this hospital management suite, payroll, point of sale, and business-workflow modules.

- 🌐 [codenest.co.tz](https://codenest.co.tz)
- 💻 [github.com/lemalbin](https://github.com/lemalbin)
- 📧 asanterabialbin@gmail.com

_The OPD module is published as an open-source work sample. Licensed under LGPL-3._
