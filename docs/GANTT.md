## Carta Gantt (PMBOK/WBS)

Cronograma del proyecto con metodologia hibrida PMBOK/Agile (17 tareas atomicas WBS).

```mermaid
gantt
    title Carta Gantt - Fraud Detection DataOps
    dateFormat YYYY-MM-DD
    axisFormat %d-%b

    section Gestion y Planificacion
    Justificar metodologia PMBOK/Agile     :done,    t1, 2026-05-13, 2d
    Crear Carta Gantt / WBS                :done,    t2, 2026-05-14, 1d
    Definir roles DataOps del equipo       :done,    t3, 2026-05-14, 1d

    section Infraestructura
    Configurar Dockerfile y requirements   :done,    t4, 2026-05-14, 2d
    Estructurar repositorio y .gitignore   :done,    t5, 2026-05-14, 1d

    section Pipeline - Dia 1
    Script 01 - Ingesta de datos           :done,    t6, 2026-05-15, 1d
    Script 02 - Enmascaramiento PII        :done,    t7, 2026-05-15, 1d
    Script 02 - Limpieza e imputacion      :done,    t8, 2026-05-15, 1d

    section Pipeline - Dia 2
    Script 03 - Validacion Estructural     :done,    t9, 2026-05-16, 1d
    Script 04 - Carga de datos finales     :done,    t10, 2026-05-16, 1d
    Configurar Logs centralizados          :done,    t11, 2026-05-16, 1d

    section Modelamiento y Despliegue
    Script 05 - Entrenar XGBoost           :done,    t15, 2026-05-17, 1d
    Desarrollar app Streamlit              :done,    t16, 2026-05-17, 1d
    Desplegar en Render y actualizar docs  :done,    t17, 2026-05-17, 1d

    section Monitoreo y Documentacion
    Definir KPIs y Plan de Escalabilidad   :active,  t12, 2026-05-18, 1d
    Ensamblar Informe Tecnico 10-12 pag    :         t13, 2026-05-18, 2d

    section Hitos
    Entrega de entregables                 :milestone, m1, 2026-05-20, 0d

    section Defensa
    Preparar y ensayar Demo en vivo        :         t14, 2026-05-21, 1d
    Defensa oral 15 min                    :milestone, m2, 2026-05-22, 0d
```

## Agrupacion de tareas por dia

| Dia | Tareas |
|-----|--------|
| 13-14 May | Gestion PMBOK, Carta Gantt, Roles, Dockerfile, Repositorio |
| 15 May | Script 01, Script 02 (Enmascaramiento + Limpieza) |
| 16 May | Script 03, Script 04, Logs centralizados |
| 17 May | Script 05 (XGBoost), Streamlit, Deploy Render |
| 18-19 May | KPIs, Informe Tecnico |
| 20 May | **Entrega** |
| 21 May | Ensayo Demo |
| 22 May | **Defensa oral** |
