from app.main import app


def contract() -> dict:
    return app.openapi()


def component(name: str) -> dict:
    return contract()["components"]["schemas"][name]


def properties(name: str) -> set[str]:
    return set(component(name).get("properties", {}))


def schema_ref(path: str, method: str, status_code: str) -> str:
    response = contract()["paths"][path][method]["responses"][status_code]
    return response["content"]["application/json"]["schema"]["$ref"]


def request_ref(path: str, method: str) -> str:
    request_body = contract()["paths"][path][method]["requestBody"]
    return request_body["content"]["application/json"]["schema"]["$ref"]


def test_contract_metadata_and_paths() -> None:
    schema = contract()

    assert schema["info"]["title"] == "Laboratorio API REST"
    assert schema["info"]["version"] == "2.0.0"

    expected_paths = {
        "/",
        "/health",
        "/sustancias",
        "/sustancias/alertas",
        "/sustancias/{sustancia_id}",
        "/movimientos",
        "/movimientos/{movimiento_id}",
        "/usuarios",
        "/usuarios/{usuario_id}",
    }
    assert set(schema["paths"]) == expected_paths


def test_resource_methods_are_part_of_the_contract() -> None:
    paths = contract()["paths"]

    assert set(paths["/sustancias"]) == {"get", "post"}
    assert set(paths["/sustancias/{sustancia_id}"]) == {"get", "put", "delete"}
    assert set(paths["/sustancias/alertas"]) == {"get"}
    assert set(paths["/movimientos"]) == {"get", "post"}
    assert set(paths["/movimientos/{movimiento_id}"]) == {"get", "put", "delete"}
    assert set(paths["/usuarios"]) == {"get", "post"}
    assert set(paths["/usuarios/{usuario_id}"]) == {"get", "put", "delete"}


def test_create_and_update_payloads_do_not_accept_client_ids() -> None:
    expected_payloads = {
        "SustanciaCreate": {
            "nombre",
            "categoria",
            "cantidad",
            "unidad",
            "nivel_riesgo",
            "ubicacion",
            "responsable",
            "cantidad_minima",
            "cantidad_maxima",
        },
        "SustanciaUpdate": {
            "nombre",
            "categoria",
            "cantidad",
            "unidad",
            "nivel_riesgo",
            "ubicacion",
            "responsable",
            "cantidad_minima",
            "cantidad_maxima",
        },
        "MovimientoCreate": {"id_sustancia", "tipo", "cantidad", "motivo"},
        "MovimientoUpdate": {"id_sustancia", "tipo", "cantidad", "motivo"},
        "UsuarioCreate": {"nombre", "rol", "contrasena"},
        "UsuarioUpdate": {"nombre", "rol", "contrasena"},
    }

    for schema_name, expected_fields in expected_payloads.items():
        assert properties(schema_name) == expected_fields
        assert "id" not in properties(schema_name)


def test_response_models_keep_server_generated_fields_private() -> None:
    assert {
        "id",
        "nombre",
        "categoria",
        "cantidad",
        "unidad",
        "nivel_riesgo",
        "ubicacion",
        "responsable",
        "cantidad_minima",
        "cantidad_maxima",
        "estado_inventario",
        "created_at",
        "updated_at",
    } <= properties("SustanciaResponse")

    assert {"id", "id_sustancia", "tipo", "cantidad", "motivo", "fecha"} <= properties(
        "MovimientoResponse"
    )

    assert {"id", "nombre", "rol", "created_at", "updated_at"} <= properties(
        "UsuarioResponse"
    )
    assert "contrasena" not in properties("UsuarioResponse")

    assert properties("MovimientoCreatedResponse") == {
        "mensaje",
        "movimiento",
        "sustancia",
    }


def test_endpoint_payload_and_response_refs() -> None:
    assert request_ref("/sustancias", "post") == "#/components/schemas/SustanciaCreate"
    assert schema_ref("/sustancias", "post", "201") == "#/components/schemas/SustanciaResponse"
    assert request_ref("/sustancias/{sustancia_id}", "put") == (
        "#/components/schemas/SustanciaUpdate"
    )
    assert schema_ref("/sustancias/{sustancia_id}", "put", "200") == (
        "#/components/schemas/SustanciaResponse"
    )

    assert request_ref("/movimientos", "post") == "#/components/schemas/MovimientoCreate"
    assert schema_ref("/movimientos", "post", "201") == (
        "#/components/schemas/MovimientoCreatedResponse"
    )
    assert request_ref("/movimientos/{movimiento_id}", "put") == (
        "#/components/schemas/MovimientoUpdate"
    )
    assert schema_ref("/movimientos/{movimiento_id}", "put", "200") == (
        "#/components/schemas/MovimientoResponse"
    )

    assert request_ref("/usuarios", "post") == "#/components/schemas/UsuarioCreate"
    assert schema_ref("/usuarios", "post", "201") == "#/components/schemas/UsuarioResponse"
    assert request_ref("/usuarios/{usuario_id}", "put") == (
        "#/components/schemas/UsuarioUpdate"
    )
    assert schema_ref("/usuarios/{usuario_id}", "put", "200") == (
        "#/components/schemas/UsuarioResponse"
    )


def test_query_parameter_contract() -> None:
    sustancias_params = {
        parameter["name"]
        for parameter in contract()["paths"]["/sustancias"]["get"]["parameters"]
    }
    movimientos_params = {
        parameter["name"]
        for parameter in contract()["paths"]["/movimientos"]["get"]["parameters"]
    }

    assert sustancias_params == {"nombre", "categoria", "nivel_riesgo", "estado"}
    assert movimientos_params == {"id_sustancia", "tipo"}
