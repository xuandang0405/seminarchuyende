import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  SafeAreaView,
  Alert,
} from "react-native";
import MapView, { Marker, Circle, Polyline } from "react-native-maps";
import { api } from "../services/api";
import { locationService } from "../services/LocationService";
import { geofenceEngine } from "../services/GeofenceEngine";
import { narrationController } from "../services/NarrationController";
import { tourSessionService } from "../services/TourSessionService";
import AudioPlayerBar from "../components/AudioPlayerBar";
import POIDetailModal from "../components/POIDetailModal";
import SettingsModal from "../components/SettingsModal";
import TourModal from "../components/TourModal";

// District 4 default map viewport
const DISTRICT_4_REGION = {
  latitude: 10.7635,
  longitude: 106.7042,
  latitudeDelta: 0.022,
  longitudeDelta: 0.022,
};

// District 4 walking route polyline (Bến Nhà Rồng -> Cầu Mống -> Chợ Xóm Chiếu -> Vĩnh Khánh)
const WALKING_TOUR_POINTS = [
  { latitude: 10.76814, longitude: 106.70678 },
  { latitude: 10.7674, longitude: 106.7061 },
  { latitude: 10.7685, longitude: 106.7055 },
  { latitude: 10.76895, longitude: 106.70488 },
  { latitude: 10.7672, longitude: 106.7032 },
  { latitude: 10.7645, longitude: 106.7038 },
  { latitude: 10.76135, longitude: 106.70425 },
  { latitude: 10.7602, longitude: 106.7018 },
  { latitude: 10.75882, longitude: 106.70012 },
];

export default function MapScreen({ onNavigateQR, onNavigateOffline }) {
  const mapRef = useRef(null);
  const [pois, setPois] = useState([]);
  const [userLocation, setUserLocation] = useState(null);
  const [currentLang, setCurrentLang] = useState("vi");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");

  // Player State
  const [playerState, setPlayerState] = useState(narrationController.getStateSnapshot());

  // Modals
  const [selectedPoiForModal, setSelectedPoiForModal] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showTourModal, setShowTourModal] = useState(false);
  const [activeTour, setActiveTour] = useState(null);

  // Subscribe to NarrationController updates
  useEffect(() => {
    const unsubscribe = narrationController.subscribe((snapshot) => {
      setPlayerState(snapshot);
    });
    return () => unsubscribe();
  }, []);

  // Load active tour
  useEffect(() => {
    tourSessionService.init().then(() => {
      setActiveTour(tourSessionService.getActiveTour());
    });
  }, []);

  // Initialize Location & Watch GPS
  useEffect(() => {
    (async () => {
      const granted = await locationService.requestPermission();
      if (!granted) {
        Alert.alert(
          "Cần quyền GPS",
          "Vui lòng cho phép quyền truy cập vị trí để hệ thống tự động phát thuyết minh khi đến gần điểm đến."
        );
      } else {
        const initialLoc = await locationService.getCurrentLocation();
        if (initialLoc) setUserLocation(initialLoc);
      }

      await locationService.startWatching((coords) => {
        setUserLocation(coords);
      });
    })();

    return () => {
      locationService.stopWatching();
    };
  }, []);

  // Fetch POIs whenever language or category changes
  useEffect(() => {
    loadPOIs();
  }, [currentLang, selectedCategory]);

  const loadPOIs = async () => {
    const data = await api.getPOIs({
      lang: currentLang,
      category: selectedCategory === "all" ? null : selectedCategory,
    });
    setPois(data);
  };

  // Real-time Geofence Evaluation when userLocation updates
  useEffect(() => {
    if (!userLocation || pois.length === 0) return;

    const winner = geofenceEngine.evaluateLocation(userLocation, pois);
    if (winner) {
      console.log(`[Geofence] Triggering POI: ${winner.poi.name} (dist: ${Math.round(winner.distance)}m)`);
      narrationController.requestNarration(winner.poi, "gps", currentLang);
    }
  }, [userLocation, pois, currentLang]);

  // Filtered POIs based on search query
  const filteredPois = pois.filter((p) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (p.name && p.name.toLowerCase().includes(q)) ||
      (p.address && p.address.toLowerCase().includes(q)) ||
      (p.description && p.description.toLowerCase().includes(q))
    );
  });

  const categories = [
    { id: "all", label: "Tất cả" },
    { id: "culinary", label: "Ẩm thực" },
    { id: "historical", label: "Di tích" },
    { id: "bridge", label: "Cầu & Cảng" },
    { id: "cultural", label: "Văn hóa" },
  ];

  return (
    <SafeAreaView style={styles.container}>
      {/* Map View */}
      <MapView
        ref={mapRef}
        style={StyleSheet.absoluteFillObject}
        initialRegion={DISTRICT_4_REGION}
        showsUserLocation
        showsMyLocationButton={false}
      >
        {/* Walking Tour Polyline */}
        <Polyline
          coordinates={WALKING_TOUR_POINTS}
          strokeColor="#ff6b35"
          strokeWidth={4}
          lineDashPattern={[0]}
        />

        {/* POI Markers & Trigger Geofence Circles */}
        {filteredPois.map((poi) => {
          if (!poi.location || !poi.location.coordinates) return null;
          const [lng, lat] = poi.location.coordinates;
          const radius = poi.trigger_radius || 30;
          const isSelected = playerState.poi?._id === poi._id;

          return (
            <React.Fragment key={poi._id}>
              {/* Trigger Geofence Boundary */}
              <Circle
                center={{ latitude: lat, longitude: lng }}
                radius={radius}
                fillColor={isSelected ? "rgba(255, 107, 53, 0.25)" : "rgba(0, 180, 216, 0.12)"}
                strokeColor={isSelected ? "#ff6b35" : "#00b4d8"}
                strokeWidth={1.5}
              />

              {/* Marker Pin */}
              <Marker
                coordinate={{ latitude: lat, longitude: lng }}
                onPress={() => setSelectedPoiForModal(poi)}
              >
                <View style={[styles.markerPin, isSelected && styles.markerPinActive]}>
                  <Text style={styles.markerIcon}>
                    {poi.category === "culinary" ? "🍲" : poi.category === "historical" ? "🏛️" : "📍"}
                  </Text>
                </View>
              </Marker>
            </React.Fragment>
          );
        })}
      </MapView>

      {/* Top Search & Filter Bar */}
      <View style={styles.topBar}>
        <View style={styles.searchRow}>
          <View style={styles.searchBox}>
            <Text style={styles.searchIcon}>🔍</Text>
            <TextInput
              style={styles.searchInput}
              placeholder="Tìm địa điểm, quán ăn Quận 4..."
              placeholderTextColor="#94a3b8"
              value={searchQuery}
              onChangeText={setSearchQuery}
            />
            {searchQuery ? (
              <TouchableOpacity onPress={() => setSearchQuery("")}>
                <Text style={styles.clearText}>✕</Text>
              </TouchableOpacity>
            ) : null}
          </View>

          <TouchableOpacity
            style={styles.iconButton}
            onPress={() => setShowSettings(true)}
          >
            <Text style={{ fontSize: 18 }}>⚙️</Text>
          </TouchableOpacity>
        </View>

        {/* Category Pill Filters */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryScroll}>
          {categories.map((c) => (
            <TouchableOpacity
              key={c.id}
              style={[
                styles.categoryPill,
                selectedCategory === c.id && styles.categoryPillActive,
              ]}
              onPress={() => setSelectedCategory(c.id)}
            >
              <Text
                style={[
                  styles.categoryText,
                  selectedCategory === c.id && styles.categoryTextActive,
                ]}
              >
                {c.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Floating Action Buttons (Right side) */}
      <View style={styles.fabColumn}>
        <TouchableOpacity style={styles.fab} onPress={onNavigateQR}>
          <Text style={styles.fabIcon}>📷</Text>
          <Text style={styles.fabLabel}>Quét QR</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.fab} onPress={() => setShowTourModal(true)}>
          <Text style={styles.fabIcon}>🚶</Text>
          <Text style={styles.fabLabel}>Tour</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.fab} onPress={onNavigateOffline}>
          <Text style={styles.fabIcon}>📦</Text>
          <Text style={styles.fabLabel}>Offline</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.fab}
          onPress={async () => {
            const loc = await locationService.getCurrentLocation();
            if (loc && mapRef.current) {
              mapRef.current.animateToRegion({
                latitude: loc.latitude,
                longitude: loc.longitude,
                latitudeDelta: 0.008,
                longitudeDelta: 0.008,
              });
            }
          }}
        >
          <Text style={styles.fabIcon}>🎯</Text>
        </TouchableOpacity>
      </View>

      {/* Bottom Unified Narration Player Bar (AD16) */}
      {playerState.poi ? (
        <AudioPlayerBar
          title={playerState.title}
          subtitle={playerState.subtitle}
          triggerType={playerState.triggerType}
          isPlaying={playerState.isPlaying}
          isLoading={playerState.isLoading}
          onPlayPause={() => narrationController.togglePlayPause()}
          onClose={() => narrationController.stop(true)}
        />
      ) : null}

      {/* POI Detail Bottom Sheet Modal */}
      <POIDetailModal
        poi={selectedPoiForModal}
        visible={!!selectedPoiForModal}
        currentLang={currentLang}
        onClose={() => setSelectedPoiForModal(null)}
        onPlayAudio={(poi, type) => {
          narrationController.requestNarration(poi, type, currentLang);
        }}
      />

      {/* Tour Selection Modal */}
      <TourModal
        visible={showTourModal}
        onClose={() => setShowTourModal(false)}
        onSelectTour={(tour) => setActiveTour(tour)}
      />

      {/* Settings Modal */}
      <SettingsModal
        visible={showSettings}
        currentLang={currentLang}
        onClose={() => setShowSettings(false)}
        onSelectLang={(lang) => {
          setCurrentLang(lang);
          setShowSettings(false);
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
  topBar: {
    position: "absolute",
    top: 50,
    left: 16,
    right: 16,
    zIndex: 10,
    gap: 8,
  },
  searchRow: {
    flexDirection: "row",
    gap: 8,
  },
  searchBox: {
    flex: 1,
    height: 46,
    backgroundColor: "rgba(15, 23, 42, 0.92)",
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 6,
  },
  searchIcon: {
    marginRight: 8,
    fontSize: 14,
  },
  searchInput: {
    flex: 1,
    color: "#ffffff",
    fontSize: 14,
  },
  clearText: {
    color: "#94a3b8",
    fontSize: 16,
    padding: 4,
  },
  iconButton: {
    width: 46,
    height: 46,
    backgroundColor: "rgba(15, 23, 42, 0.92)",
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 6,
  },
  categoryScroll: {
    flexDirection: "row",
  },
  categoryPill: {
    backgroundColor: "rgba(15, 23, 42, 0.85)",
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
    marginRight: 6,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  categoryPillActive: {
    backgroundColor: "#ff6b35",
    borderColor: "#ff6b35",
  },
  categoryText: {
    color: "#94a3b8",
    fontSize: 12,
    fontWeight: "600",
  },
  categoryTextActive: {
    color: "#ffffff",
    fontWeight: "700",
  },
  fabColumn: {
    position: "absolute",
    right: 16,
    bottom: 120,
    gap: 12,
    zIndex: 10,
  },
  fab: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "rgba(15, 23, 42, 0.92)",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255, 107, 53, 0.4)",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 8,
  },
  fabIcon: {
    fontSize: 18,
  },
  fabLabel: {
    fontSize: 8,
    color: "#ff6b35",
    fontWeight: "800",
    marginTop: 1,
  },
  markerPin: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: "#1e293b",
    borderWidth: 2,
    borderColor: "#00b4d8",
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 4,
  },
  markerPinActive: {
    borderColor: "#ff6b35",
    backgroundColor: "#ff6b35",
    transform: [{ scale: 1.15 }],
  },
  markerIcon: {
    fontSize: 18,
  },
});
