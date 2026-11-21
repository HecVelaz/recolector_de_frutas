"""Validación local de GeoJSON, en metros, compatible con el editor Android."""
import math


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(feature):
    require(isinstance(feature, dict) and feature.get('type') == 'Feature', 'Se requiere Feature GeoJSON')
    props = feature.get('properties')
    require(isinstance(props, dict), 'Faltan propiedades')
    name = props.get('name')
    require(isinstance(name, str) and 1 <= len(name.strip()) <= 40, 'Nombre inválido')
    geometry = feature.get('geometry')
    require(isinstance(geometry, dict) and geometry.get('type') == 'Polygon', 'Se requiere Polygon')
    rings = geometry.get('coordinates')
    require(isinstance(rings, list) and len(rings) == 1, 'Solo se admite un anillo sin huecos')
    ring = rings[0]
    require(isinstance(ring, list) and 4 <= len(ring) <= 65, 'Se requieren 3–64 vértices')
    for point in ring:
        require(isinstance(point, list) and len(point) == 2, 'Coordenadas [longitud, latitud]')
        require(all(type(v) in (int, float) and math.isfinite(v) for v in point), 'Coordenadas no finitas')
        require(-180 <= point[0] <= 180 and -85 <= point[1] <= 85, 'Coordenadas fuera de rango')
    require(ring[0] == ring[-1], 'Anillo sin cerrar')
    origin = ring[0]
    xy = [((p[0] - origin[0]) * math.pi / 180 * 6371000 * math.cos(math.radians(origin[1])),
           (p[1] - origin[1]) * math.pi / 180 * 6371000) for p in ring[:-1]]
    signed = validate_metric_polygon(xy)
    vertices = ring[:-1] if signed > 0 else list(reversed(ring[:-1]))
    normalized = {'type':'Feature', 'properties':{'name':name.strip(), 'schemaVersion':1, 'purpose':'operation_boundary'},
                  'geometry':{'type':'Polygon', 'coordinates':[vertices + [vertices[0]]]}}
    return normalized, abs(signed)


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def on_segment(a, b, p):
    return abs(cross(a, b, p)) < 1e-6 and all(min(a[k], b[k])-1e-6 <= p[k] <= max(a[k], b[k])+1e-6 for k in (0, 1))


def intersects(a, b, c, d):
    proper = cross(a, b, c)*cross(a, b, d) < 0 and cross(c, d, a)*cross(c, d, b) < 0
    return proper or any((on_segment(a,b,c), on_segment(a,b,d), on_segment(c,d,a), on_segment(c,d,b)))


def validate_metric_polygon(xy):
    """Área firmada de un polígono simple en metros, sin vértice de cierre."""
    require(3 <= len(xy) <= 64, 'Se requieren 3–64 vértices')
    require(all(isinstance(p, (list, tuple)) and len(p) == 2
                and all(type(v) in (int, float) and math.isfinite(v) for v in p) for p in xy),
            'Coordenadas métricas inválidas')
    require(all(math.hypot(*p) <= 5000 for p in xy), 'El área excede el entorno local de 5 km')
    n = len(xy)
    require(all(math.dist(xy[i], xy[j]) >= .25 for i in range(n) for j in range(i)), 'Vértices demasiado próximos')
    for i in range(n):
        a, b, c = xy[i-1], xy[i], xy[(i+1) % n]
        require(not (on_segment(a,b,c) or on_segment(b,c,a)), 'Lados adyacentes superpuestos')
        for j in range(i+1, n):
            if j == i+1 or (i == 0 and j == n-1):
                continue
            require(not intersects(xy[i], xy[(i+1) % n], xy[j], xy[(j+1) % n]), 'Lados cruzados o en contacto')
    signed = sum(xy[i][0]*xy[(i+1)%n][1] - xy[(i+1)%n][0]*xy[i][1] for i in range(n))/2
    require(abs(signed) >= 1, 'Área menor a 1 m²')
    return signed
