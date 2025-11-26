# State Machine System Overview

## Enums and State Definitions

### EstadoProyecto (Proyecto States)
- **PENDIENTE**: Created and seeking financing
- **EN_EJECUCION**: Project is being executed  
- **FINALIZADO**: Work completed and closed

### EstadoEtapa (Stage States)
- **PENDIENTE**: Awaiting funding (default state)
- **FINANCIADA**: All pedidos are at least COMPROMETIDO
- **ESPERANDO_EJECUCION**: All pedidos financed, waiting for manual start (set when project starts)
- **EN_EJECUCION**: Stage is in execution (manual transition via start_etapa endpoint)
- **COMPLETADA**: All pedidos are COMPLETADO

### EstadoPedido (Coverage Request States)
- **PENDIENTE**: No accepted oferta yet (default state)
- **COMPROMETIDO**: An oferta has been accepted, awaiting fulfillment
- **COMPLETADO**: Pedido fulfilled

### EstadoOferta (Offer States)
- **PENDIENTE**: Pending review (default state)
- **ACEPTADA**: Accepted by project owner
- **RECHAZADA**: Rejected (either manually or auto-rejected when another oferta accepted)

### TipoPedido (Coverage Request Types)
- **ECONOMICO**: Economic/financial request
- **MATERIALES**: Materials request
- **MANO_OBRA**: Labor request
- **TRANSPORTE**: Transport request
- **EQUIPAMIENTO**: Equipment request

## State Machine Implementation

### Location
- Main functions: `/app/services/state_machine.py`
- Helper functions for etapa state calculation

### Key Functions

1. **etapa_pedidos_pendientes(etapa: Etapa) -> List[Pedido]**
   - Returns pedidos that are still in PENDIENTE state
   - Used to check if etapa can advance from PENDIENTE

2. **etapa_all_pedidos_financed(etapa: Etapa) -> bool**
   - True when all pedidos are at least COMPROMETIDO (no PENDIENTE pedidos remain)
   - Checks if etapa can transition to FINANCIADA

3. **etapa_all_pedidos_completed(etapa: Etapa) -> bool**
   - True when ALL pedidos are COMPLETADO
   - Checks if etapa can transition to COMPLETADA

4. **refresh_etapa_state(etapa: Etapa) -> EstadoEtapa**
   - Recalculates etapa.estado based on its pedidos
   - Called after any state change that affects pedidos
   - State transitions:
     - PENDIENTE -> FINANCIADA: When all pedidos are at least COMPROMETIDO
     - FINANCIADA/PENDIENTE -> COMPLETADA: When all pedidos are COMPLETADO
     - EN_EJECUCION: Locked - stays EN_EJECUCION until completion (fecha_completitud preserved)
   - Also manages fecha_completitud timestamp

## State Transition Flows

### Oferta Acceptance Flow
1. Project owner calls `OfertaService.accept(oferta_id)`
2. Checks: Only PENDIENTE ofertas can be accepted
3. Checks: Only for pedidos in PENDIENTE state
4. Actions:
   - Oferta.estado -> ACEPTADA
   - All other PENDIENTE ofertas for same pedido -> RECHAZADA (auto)
   - Pedido.estado -> COMPROMETIDO (via PedidoService.mark_as_comprometido)
   - refresh_etapa_state() called to update etapa state
5. Etapa.estado transitions:
   - PENDIENTE -> FINANCIADA (if all pedidos now comprometido)

### Oferta Rejection Flow
1. Project owner calls `OfertaService.reject(oferta_id)`
2. Checks: Only PENDIENTE ofertas can be rejected
3. Actions:
   - Oferta.estado -> RECHAZADA
   - Pedido remains PENDIENTE (no state change)

### Pedido State Transitions
1. **PENDIENTE -> COMPROMETIDO**
   - Triggered by accepting an oferta
   - Called via `PedidoService.mark_as_comprometido()`
   - Refreshes etapa state

2. **COMPROMETIDO -> COMPLETADO**
   - Called via `PedidoService.mark_as_completed()`
   - Used when oferente confirms fulfillment
   - Refreshes etapa state

### Etapa State Transitions

#### Automatic Transitions (via refresh_etapa_state)
- **PENDIENTE -> FINANCIADA**: Automatic when all pedidos reach COMPROMETIDO
- **FINANCIADA -> COMPLETADA**: Automatic when all pedidos reach COMPLETADO
- **PENDIENTE/FINANCIADA -> PENDIENTE**: If a COMPLETADO pedido regresses (edge case)

#### Manual Transitions
- **FINANCIADA -> ESPERANDO_EJECUCION**: When project starts (all pedidos financed)
- **ESPERANDO_EJECUCION -> EN_EJECUCION**: When calling start_etapa endpoint (Bonita or owner)
- **EN_EJECUCION -> COMPLETADA**: When calling complete_etapa endpoint (owner only)

## Service Layer Integration

### Where refresh_etapa_state is called:
1. `PedidoService.mark_as_comprometido()` - After pedido accepted
2. `PedidoService.mark_as_completed()` - After pedido fulfilled
3. `ProyectoService.create()` - When creating project with initial etapas/pedidos
4. `ProyectoService.update()` - When updating project structure

## Key Characteristics

1. **Automatic State Propagation**: Changes bubble up from pedidos -> etapas
2. **Eventual Consistency**: Etapa state calculated on-demand via refresh_etapa_state()
3. **Cascade Deletions**: Parent deletion cascades to all children
4. **Completion Timestamps**: fecha_completitud tracks when stages complete
5. **Auto-rejection**: Accepting one oferta automatically rejects competing offers
6. **No Backwards Transitions**: States only move forward (PENDIENTE -> COMPROMETIDO -> COMPLETADO)
7. **EN_EJECUCION Lock**: Once in execution, etapa stays there until completion

## Validation Rules

1. Can only accept ofertas for PENDIENTE pedidos
2. Can only accept PENDIENTE ofertas
3. Can only reject PENDIENTE ofertas
4. No direct pedido estado updates - only through service methods
5. Etapa estado auto-calculated from pedidos
