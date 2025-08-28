// ===== app/build.gradle.kts (module-level) =====
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    // Applica Google Services QUI (Firebase)
    id("com.google.gms.google-services")
    // Plugin Flutter dell'app (solo qui)
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.example.app_eventi"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    defaultConfig {
        applicationId = "com.example.app_eventi"
        minSdk = 21
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        multiDexEnabled = true
    }

    buildTypes {
        release {
            // per test: usa keystore debug; per publish configura una release key
            signingConfig = signingConfigs.getByName("debug")

            // lascia off finché non è tutto stabile
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            // nulla di speciale
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.multidex:multidex:2.0.1")
}

flutter { source = "../.." }
