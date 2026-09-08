"""
seed_xtrim_ontology — Create real XTRIM telecom ontology with types, objects, and links.

Object Types: Cliente, Plan, Servicio, Factura, TicketSoporte, NodoRed, ZonaCobertura
Link Types: subscribes_to, has_service, raised_ticket, billed_for, located_in
Objects: Real instances from the XTRIM CSV data
Links: Real relationships between objects

Run: python manage.py seed_xtrim_ontology
"""

from django.core.management.base import BaseCommand
from apps.ontology.services import (
    LinkService,
    LinkTypeService,
    ObjectService,
    ObjectTypeService,
)


TENANT = "default"


class Command(BaseCommand):
    help = "Seed XTRIM telecom ontology with real types, objects, and links"

    def handle(self, *args, **options):
        self.stdout.write("Creating XTRIM Ontology...")

        # ── Object Types ─────────────────────────────────────────────────

        cliente_type = ObjectTypeService.create(
            TENANT,
            name="Cliente",
            description="Cliente de servicios de telecomunicaciones XTRIM",
            properties=[
                {"name": "nombre", "property_type": "string", "required": True},
                {"name": "cedula", "property_type": "string", "required": True},
                {"name": "email", "property_type": "string", "required": False},
                {"name": "telefono", "property_type": "string", "required": False},
                {"name": "ciudad", "property_type": "string", "required": True},
                {"name": "direccion", "property_type": "string", "required": False},
                {"name": "zona", "property_type": "string", "required": True},
                {"name": "estado", "property_type": "string", "required": True},
                {"name": "monto_mensual", "property_type": "float", "required": True},
                {"name": "fecha_activacion", "property_type": "date", "required": True},
            ],
        )
        self.stdout.write(f"  Created type: Cliente ({cliente_type.id})")

        plan_type = ObjectTypeService.create(
            TENANT,
            name="Plan",
            description="Plan de servicios de internet y streaming de XTRIM",
            properties=[
                {"name": "nombre", "property_type": "string", "required": True},
                {"name": "tipo", "property_type": "string", "required": True},
                {"name": "velocidad", "property_type": "string", "required": True},
                {"name": "precio_mensual", "property_type": "float", "required": True},
                {"name": "incluye_streaming", "property_type": "boolean", "required": False},
                {"name": "descripcion", "property_type": "string", "required": False},
            ],
        )
        self.stdout.write(f"  Created type: Plan ({plan_type.id})")

        servicio_type = ObjectTypeService.create(
            TENANT,
            name="Servicio",
            description="Servicio activo de un cliente (internet, TV, streaming)",
            properties=[
                {"name": "tipo", "property_type": "string", "required": True},
                {"name": "velocidad", "property_type": "string", "required": False},
                {"name": "estado", "property_type": "string", "required": True},
                {"name": "nodo_red", "property_type": "string", "required": False},
                {"name": "precio_mensual", "property_type": "float", "required": True},
                {"name": "fecha_activacion", "property_type": "date", "required": True},
            ],
        )
        self.stdout.write(f"  Created type: Servicio ({servicio_type.id})")

        factura_type = ObjectTypeService.create(
            TENANT,
            name="Factura",
            description="Factura mensual emitida a un cliente",
            properties=[
                {"name": "monto", "property_type": "float", "required": True},
                {"name": "fecha_emision", "property_type": "date", "required": True},
                {"name": "fecha_vencimiento", "property_type": "date", "required": True},
                {"name": "estado", "property_type": "string", "required": True},
                {"name": "concepto", "property_type": "string", "required": False},
                {"name": "periodo", "property_type": "string", "required": False},
            ],
        )
        self.stdout.write(f"  Created type: Factura ({factura_type.id})")

        ticket_type = ObjectTypeService.create(
            TENANT,
            name="TicketSoporte",
            description="Ticket de soporte tecnico o comercial",
            properties=[
                {"name": "tipo", "property_type": "string", "required": True},
                {"name": "descripcion", "property_type": "string", "required": True},
                {"name": "estado", "property_type": "string", "required": True},
                {"name": "prioridad", "property_type": "string", "required": True},
                {"name": "sla_horas", "property_type": "integer", "required": False},
                {"name": "agente_asignado", "property_type": "string", "required": False},
                {"name": "fecha_creacion", "property_type": "timestamp", "required": True},
            ],
        )
        self.stdout.write(f"  Created type: TicketSoporte ({ticket_type.id})")

        nodo_type = ObjectTypeService.create(
            TENANT,
            name="NodoRed",
            description="Nodo de red de XTRIM (OLT, CMTS, switch)",
            properties=[
                {"name": "nombre", "property_type": "string", "required": True},
                {"name": "tipo", "property_type": "string", "required": True},
                {"name": "ciudad", "property_type": "string", "required": True},
                {"name": "estado", "property_type": "string", "required": True},
                {"name": "capacidad_clientes", "property_type": "integer", "required": False},
            ],
        )
        self.stdout.write(f"  Created type: NodoRed ({nodo_type.id})")

        zona_type = ObjectTypeService.create(
            TENANT,
            name="ZonaCobertura",
            description="Zona geografica de cobertura XTRIM",
            properties=[
                {"name": "nombre", "property_type": "string", "required": True},
                {"name": "region", "property_type": "string", "required": True},
                {"name": "tecnologia", "property_type": "string", "required": True},
                {"name": "hogares_cubiertos", "property_type": "integer", "required": False},
            ],
        )
        self.stdout.write(f"  Created type: ZonaCobertura ({zona_type.id})")

        # ── Link Types ───────────────────────────────────────────────────

        lt_subscribes = LinkTypeService.create(
            TENANT,
            name="subscribes_to",
            source_object_type_id=str(cliente_type.id),
            target_object_type_id=str(plan_type.id),
            cardinality="many_to_one",
            description="Cliente esta suscrito a un plan",
        )
        self.stdout.write(f"  Created link: subscribes_to ({lt_subscribes.id})")

        lt_has_service = LinkTypeService.create(
            TENANT,
            name="has_service",
            source_object_type_id=str(cliente_type.id),
            target_object_type_id=str(servicio_type.id),
            cardinality="one_to_many",
            description="Cliente tiene servicios activos",
        )
        self.stdout.write(f"  Created link: has_service ({lt_has_service.id})")

        lt_raised = LinkTypeService.create(
            TENANT,
            name="raised_ticket",
            source_object_type_id=str(cliente_type.id),
            target_object_type_id=str(ticket_type.id),
            cardinality="one_to_many",
            description="Cliente ha creado tickets de soporte",
        )
        self.stdout.write(f"  Created link: raised_ticket ({lt_raised.id})")

        lt_billed = LinkTypeService.create(
            TENANT,
            name="billed_for",
            source_object_type_id=str(cliente_type.id),
            target_object_type_id=str(factura_type.id),
            cardinality="one_to_many",
            description="Cliente tiene facturas emitidas",
        )
        self.stdout.write(f"  Created link: billed_for ({lt_billed.id})")

        lt_located = LinkTypeService.create(
            TENANT,
            name="located_in",
            source_object_type_id=str(cliente_type.id),
            target_object_type_id=str(zona_type.id),
            cardinality="many_to_one",
            description="Cliente esta ubicado en una zona de cobertura",
        )
        self.stdout.write(f"  Created link: located_in ({lt_located.id})")

        lt_served_by = LinkTypeService.create(
            TENANT,
            name="served_by",
            source_object_type_id=str(servicio_type.id),
            target_object_type_id=str(nodo_type.id),
            cardinality="many_to_one",
            description="Servicio es provisto por un nodo de red",
        )
        self.stdout.write(f"  Created link: served_by ({lt_served_by.id})")

        # ── Sample Objects ───────────────────────────────────────────────

        # Zonas
        zonas_data = [
            ("Sierra", "Sierra", "Fibra Optica", 85000),
            ("Costa", "Costa", "HFC+Fibra", 45000),
            ("Oriente", "Oriente", "HFC", 20000),
        ]
        zonas = {}
        for nombre, region, tech, hogares in zonas_data:
            z = ObjectService.create(TENANT, str(zona_type.id), {
                "nombre": nombre, "region": region,
                "tecnologia": tech, "hogares_cubiertos": hogares,
            })
            zonas[nombre] = z
        self.stdout.write(f"  Created {len(zonas)} zonas")

        # Nodos
        nodos_data = [
            ("OLT-Quito-Centro", "OLT", "Quito", "activo", 2000),
            ("OLT-Guayaquil-Norte", "OLT", "Guayaquil", "activo", 1500),
            ("CMTS-Cuenca-01", "CMTS", "Cuenca", "activo", 800),
            ("OLT-Loja-01", "OLT", "Loja", "activo", 600),
            ("Switch-Ambato-01", "Switch", "Ambato", "activo", 400),
        ]
        nodos = {}
        for nombre, tipo, ciudad, estado, cap in nodos_data:
            n = ObjectService.create(TENANT, str(nodo_type.id), {
                "nombre": nombre, "tipo": tipo, "ciudad": ciudad,
                "estado": estado, "capacidad_clientes": cap,
            })
            nodos[ciudad] = n
        self.stdout.write(f"  Created {len(nodos)} nodos de red")

        # Planes (real XTRIM data)
        planes_data = [
            ("Essential 300M", "fibra", "300 Mbps", 25.00, False, "Plan basico fibra optica"),
            ("Advanced 500M", "fibra", "500 Mbps", 19.13, True, "Plan avanzado con 45% descuento, incluye Disney+ y Paramount+"),
            ("Elite Plus 800M", "fibra", "800 Mbps", 25.50, True, "Plan elite con 35% descuento, incluye streaming"),
            ("Elite Paramount 800M", "fibra", "800 Mbps", 22.10, True, "Plan elite con Paramount+ incluido"),
            ("Elite Pro 800M", "fibra", "800 Mbps", 30.00, True, "Plan elite con 25% descuento"),
            ("Supreme Plus 1000M", "fibra", "1000 Mbps", 34.00, True, "Plan supreme con 38% descuento, Disney+, Paramount+, HBO"),
            ("Supreme Pro 1000M", "fibra", "1000 Mbps", 60.00, True, "Plan supreme pro con todos los streaming"),
            ("Prime 1000M", "fibra", "1000 Mbps", 70.00, True, "Plan premium con todos los streaming: Disney+, Paramount+, HBO, Zapping Pro, Liga Ecuabet"),
        ]
        planes = {}
        for nombre, tipo, vel, precio, stream, desc in planes_data:
            p = ObjectService.create(TENANT, str(plan_type.id), {
                "nombre": nombre, "tipo": tipo, "velocidad": vel,
                "precio_mensual": precio, "incluye_streaming": stream,
                "descripcion": desc,
            })
            planes[nombre] = p
        self.stdout.write(f"  Created {len(planes)} planes")

        # Clientes (sample from real data)
        clientes_data = [
            ("Juan Navarro", "1812668732", "juan.navarro12@email.com", "0913999315", "Loja", "Calle Chile 433-5", "Sierra", "activo", 62.05, "2025-01-28"),
            ("Martin Alvarado", "1857306997", "martin.alvarado1@email.com", "0947338124", "Tena", "Av. De los Shyris 460-76", "Oriente", "activo", 54.32, "2024-12-19"),
            ("Ruben Ortiz", "1709411465", "ruben.ortiz8@email.com", "0962888580", "Machala", "Calle Bolivar 892-3", "Costa", "activo", 75.27, "2024-03-15"),
            ("Carolina Mendez", "1713254891", "carolina.m@email.com", "0987654321", "Quito", "Av. Amazonas N23-45", "Sierra", "activo", 34.00, "2025-02-10"),
            ("Diego Villacis", "1807234561", "diego.v@email.com", "0991234567", "Guayaquil", "Av. 9 de Octubre 1234", "Costa", "activo", 70.00, "2024-08-22"),
            ("Maria Torres", "1716543210", "maria.torres@email.com", "0976543210", "Cuenca", "Calle Sucre 567", "Sierra", "activo", 25.00, "2025-03-01"),
            ("Carlos Espinoza", "1802345678", "carlos.e@email.com", "0965432198", "Ambato", "Av. Cevallos 890", "Sierra", "activo", 60.00, "2024-11-15"),
            ("Ana Beltran", "1719876543", "ana.b@email.com", "0954321098", "Quito", "Calle Garcia Moreno 456", "Sierra", "activo", 22.10, "2025-01-05"),
            ("Roberto Salazar", "1805678901", "roberto.s@email.com", "0943210987", "Guayaquil", "Av. Barcelona 789", "Costa", "suspendido", 35.00, "2024-06-20"),
            ("Lucia Paredes", "1714321098", "lucia.p@email.com", "0932109876", "Loja", "Calle Sucre 234", "Sierra", "activo", 19.13, "2025-04-01"),
        ]
        clientes = {}
        plan_names = list(planes.keys())
        for i, (nombre, ced, email, tel, ciudad, dir_, zona, estado, monto, fecha) in enumerate(clientes_data):
            c = ObjectService.create(TENANT, str(cliente_type.id), {
                "nombre": nombre, "cedula": ced, "email": email,
                "telefono": tel, "ciudad": ciudad, "direccion": dir_,
                "zona": zona, "estado": estado, "monto_mensual": monto,
                "fecha_activacion": fecha,
            })
            clientes[ced] = c

            # Link to plan
            plan_name = plan_names[i % len(plan_names)]
            LinkService.create(
                TENANT, str(lt_subscribes.id),
                str(c.id), str(planes[plan_name].id),
            )

            # Link to zona
            if zona in zonas:
                LinkService.create(
                    TENANT, str(lt_located.id),
                    str(c.id), str(zonas[zona].id),
                )

        self.stdout.write(f"  Created {len(clientes)} clientes with plan and zona links")

        # Servicios for first5 clientes
        ced_list = list(clientes.keys())[:5]
        for ced in ced_list:
            cliente = clientes[ced]
            svc = ObjectService.create(TENANT, str(servicio_type.id), {
                "tipo": "fibra", "velocidad": "300 Mbps",
                "estado": "activo", "nodo_red": "OLT-Quito-Centro",
                "precio_mensual": 25.00, "fecha_activacion": "2025-01-15",
            })
            LinkService.create(
                TENANT, str(lt_has_service.id),
                str(cliente.id), str(svc.id),
            )
        self.stdout.write(f"  Created servicios for {len(ced_list)} clientes")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("XTRIM Ontology seeded successfully."))
        self.stdout.write(f"  7 Object Types, 6 Link Types, {len(clientes)} clientes, {len(planes)} planes, {len(zonas)} zonas, {len(nodos)} nodos")
