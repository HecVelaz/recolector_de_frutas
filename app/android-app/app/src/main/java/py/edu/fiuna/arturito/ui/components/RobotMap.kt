package py.edu.fiuna.arturito.ui.components

import android.content.ComponentCallbacks2
import android.content.res.Configuration
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalInspectionMode
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import okhttp3.OkHttpClient
import org.maplibre.android.MapLibre
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import org.maplibre.android.module.http.HttpRequestUtil
import org.maplibre.android.style.layers.CircleLayer
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.FillLayer
import org.maplibre.android.style.layers.RasterLayer
import org.maplibre.android.style.layers.BackgroundLayer
import org.maplibre.android.style.layers.PropertyFactory.*
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.LineString
import org.maplibre.geojson.Point
import org.maplibre.geojson.Feature
import org.maplibre.geojson.FeatureCollection
import org.maplibre.geojson.Polygon
import py.edu.fiuna.arturito.model.FencePoint
import py.edu.fiuna.arturito.model.GpsFix

private object MapNetwork {
    val client = OkHttpClient.Builder().addInterceptor { chain ->
        chain.proceed(chain.request().newBuilder().header("User-Agent", "Arturito-FIUNA/0.3 (Android educational prototype)").build())
    }.build()
}

/** MapView nativo alojado en Compose, con ciclo de vida explícito y capas GeoJSON. */
@Composable
fun RobotMap(track: List<GpsFix>, followRobot: Boolean, centerRequest: Int,
             onStatus: (String) -> Unit, modifier: Modifier = Modifier,
             fence: List<FencePoint> = emptyList(), fenceClosed: Boolean = false,
             selectedVertex: Int? = null, editingFence: Boolean = false,
             onFenceTap: (Double, Double, Int?) -> Unit = { _, _, _ -> }, fitFenceRequest: Int = 0) {
    if (LocalInspectionMode.current) {
        Box(modifier) { Text("MapLibre Native · mapa disponible al ejecutar la aplicación") }
        return
    }
    val context = LocalContext.current
    val dark = MaterialTheme.colorScheme.background.luminance() < .4f
    val owner = LocalLifecycleOwner.current
    val latestTrack by rememberUpdatedState(track)
    val latestStatus by rememberUpdatedState(onStatus)
    val latestEditing by rememberUpdatedState(editingFence)
    val latestTap by rememberUpdatedState(onFenceTap)
    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var style by remember { mutableStateOf<Style?>(null) }
    val view = remember(context) {
        MapLibre.getInstance(context.applicationContext)
        HttpRequestUtil.setOkHttpClient(MapNetwork.client)
        MapView(context).apply { onCreate(null) }
    }

    DisposableEffect(view, owner) {
        var destroyed = false
        var attachedMap: MapLibreMap? = null
        var clickListener: MapLibreMap.OnMapClickListener? = null
        val failure = MapView.OnDidFailLoadingMapListener {
            if (!destroyed) latestStatus("No se pudo cargar el mapa. Revisá internet y pulsá Recargar.")
        }
        view.addOnDidFailLoadingMapListener(failure)
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> view.onStart()
                Lifecycle.Event.ON_RESUME -> view.onResume()
                Lifecycle.Event.ON_PAUSE -> view.onPause()
                Lifecycle.Event.ON_STOP -> view.onStop()
                else -> Unit
            }
        }
        owner.lifecycle.addObserver(observer)
        val memory = object : ComponentCallbacks2 {
            override fun onConfigurationChanged(newConfig: Configuration) = Unit
            override fun onLowMemory() { view.onLowMemory() }
            override fun onTrimMemory(level: Int) { view.onLowMemory() }
        }
        context.applicationContext.registerComponentCallbacks(memory)
        latestStatus("Preparando mapa…")
        view.getMapAsync { readyMap ->
            if (!destroyed) {
                map = readyMap
                attachedMap = readyMap
                clickListener = MapLibreMap.OnMapClickListener { coordinate ->
                    if (!latestEditing) false else {
                        val hit = readyMap.queryRenderedFeatures(readyMap.projection.toScreenLocation(coordinate), "fence-vertices")
                            .firstOrNull()?.getNumberProperty("index")?.toInt()
                        latestTap(coordinate.latitude, coordinate.longitude, hit)
                        true
                    }
                }.also { readyMap.addOnMapClickListener(it) }
                readyMap.setStyle(Style.Builder().fromUri("asset://robot-map-style.json")) { readyStyle ->
                    if (!destroyed) {
                        readyStyle.addSource(GeoJsonSource("route"))
                        readyStyle.addSource(GeoJsonSource("robot"))
                        readyStyle.addSource(GeoJsonSource("fence-fill"))
                        readyStyle.addSource(GeoJsonSource("fence-line"))
                        readyStyle.addSource(GeoJsonSource("fence-points"))
                        readyStyle.addSource(GeoJsonSource("fence-selected"))
                        readyStyle.addLayer(FillLayer("fence-area", "fence-fill").withProperties(fillColor("#de5360"), fillOpacity(0.22f)))
                        readyStyle.addLayer(LineLayer("fence-border", "fence-line").withProperties(lineColor("#a12c32"), lineWidth(3f)))
                        readyStyle.addLayer(LineLayer("route-line", "route").withProperties(
                            lineColor("#303740"), lineWidth(5f), lineJoin("round"), lineCap("round")))
                        readyStyle.addLayer(CircleLayer("robot-marker", "robot").withProperties(
                            circleRadius(10f), circleColor("#1976d2"), circleStrokeWidth(3f), circleStrokeColor("#ffffff")))
                        readyStyle.addLayer(CircleLayer("fence-vertices", "fence-points").withProperties(
                            circleRadius(9f), circleColor("#a12c32"), circleStrokeWidth(2f), circleStrokeColor("#ffffff")))
                        readyStyle.addLayer(CircleLayer("fence-active-vertex", "fence-selected").withProperties(
                            circleRadius(12f), circleColor("#7b1fa2"), circleStrokeWidth(3f), circleStrokeColor("#ffffff")))
                        style = readyStyle
                        latestTrack.lastOrNull()?.let {
                            readyMap.moveCamera(CameraUpdateFactory.newLatLngZoom(LatLng(it.latitude, it.longitude), 17.0))
                        }
                        latestStatus("Capa GPS lista · mapa base por internet")
                    }
                }
            }
        }
        onDispose {
            destroyed = true
            owner.lifecycle.removeObserver(observer)
            context.applicationContext.unregisterComponentCallbacks(memory)
            view.removeOnDidFailLoadingMapListener(failure)
            clickListener?.let { attachedMap?.removeOnMapClickListener(it) }
            if (owner.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) view.onPause()
            if (owner.lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)) view.onStop()
            view.onDestroy()
        }
    }

    LaunchedEffect(style, dark) {
        style?.getLayerAs<BackgroundLayer>("background")
            ?.setProperties(backgroundColor(if (dark) "#252728" else "#e9ebe7"))
        style?.getLayerAs<RasterLayer>("osm")?.setProperties(
            rasterBrightnessMin(if (dark) .07f else 0f),
            rasterBrightnessMax(if (dark) .59f else 1f),
            rasterSaturation(if (dark) -.48f else 0f))
        style?.getLayerAs<LineLayer>("route-line")
            ?.setProperties(lineColor(if (dark) "#d0e2f9" else "#303740"))
    }

    LaunchedEffect(style, fence, fenceClosed, selectedVertex) {
        val empty = "{\"type\":\"FeatureCollection\",\"features\":[]}"
        val vertices = fence.map { Point.fromLngLat(it.longitude, it.latitude) }
        val ring = if (fenceClosed && vertices.size >= 3) vertices + vertices.first() else vertices
        style?.getSourceAs<GeoJsonSource>("fence-line")?.let {
            if (ring.size >= 2) it.setGeoJson(LineString.fromLngLats(ring)) else it.setGeoJson(empty)
        }
        style?.getSourceAs<GeoJsonSource>("fence-fill")?.let {
            if (fenceClosed && vertices.size >= 3) it.setGeoJson(Polygon.fromLngLats(listOf(ring))) else it.setGeoJson(empty)
        }
        val features = vertices.mapIndexed { index, point -> Feature.fromGeometry(point).apply { addNumberProperty("index", index) } }
        style?.getSourceAs<GeoJsonSource>("fence-points")?.setGeoJson(FeatureCollection.fromFeatures(features))
        style?.getSourceAs<GeoJsonSource>("fence-selected")?.let {
            if (selectedVertex != null && selectedVertex in vertices.indices) it.setGeoJson(vertices[selectedVertex]) else it.setGeoJson(empty)
        }
    }

    val points = track.map { Point.fromLngLat(it.longitude, it.latitude) }
    LaunchedEffect(style, points) {
        points.lastOrNull()?.let { style?.getSourceAs<GeoJsonSource>("robot")?.setGeoJson(it) }
        if (points.size >= 2) style?.getSourceAs<GeoJsonSource>("route")?.setGeoJson(LineString.fromLngLats(points))
        else style?.getSourceAs<GeoJsonSource>("route")?.setGeoJson("{\"type\":\"FeatureCollection\",\"features\":[]}")
    }
    LaunchedEffect(map, style, points.lastOrNull(), followRobot, centerRequest) {
        if (followRobot) track.lastOrNull()?.let {
            map?.moveCamera(CameraUpdateFactory.newLatLng(LatLng(it.latitude, it.longitude)))
        }
    }
    LaunchedEffect(map, style, fitFenceRequest) {
        if (fitFenceRequest > 0 && fence.isNotEmpty()) {
            val coordinates = fence.map { LatLng(it.latitude, it.longitude) }
            if (coordinates.size == 1) map?.moveCamera(CameraUpdateFactory.newLatLngZoom(coordinates.first(), 18.0))
            else map?.moveCamera(CameraUpdateFactory.newLatLngBounds(LatLngBounds.Builder().includes(coordinates).build(), 48))
        }
    }
    AndroidView(factory = { view }, modifier = modifier)
}
