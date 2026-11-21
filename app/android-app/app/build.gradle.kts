plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "py.edu.fiuna.arturito"
    compileSdk = 36

    defaultConfig {
        applicationId = "py.edu.fiuna.arturito"
        minSdk = 26
        targetSdk = 36
        versionCode = 22
        versionName = "0.9.0"
    }
    buildFeatures { compose = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2025.08.01"))
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("org.maplibre.gl:android-sdk:13.7.1")
    // MapLibre ya utiliza OkHttp 4.12.0; se declara para identificar nuestras solicitudes de mapas.
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    testImplementation("junit:junit:4.13.2")
    debugImplementation("androidx.compose.ui:ui-tooling")
}

tasks.withType<Test>().configureEach {
    maxHeapSize = "256m"
    maxParallelForks = 1
}
