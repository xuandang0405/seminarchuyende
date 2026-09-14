// init_mongodb.js
// Ch?y b?ng mongosh, MongoDB 8.0+

const appDb = db.getSiblingDB("tour_guide");

const collectionNames = [
  "admin_users",
  "languages",
  "pois",
  "poi_contents",
  "audio_assets",
  "tours",
  "qr_codes",
  "content_jobs",
  "tour_packages",
  "visit_sessions",
  "playbacks",
  "playback_events",
  "location_samples"
];

// Ki?m tra tru?c khi kh?i t?o.
const existing = new Set(appDb.getCollectionNames());
const collisions = collectionNames.filter(name => existing.has(name));

if (collisions.length) {
  throw new Error(
    "Script kh?i t?o: collection dã t?n t?i: " +
    collisions.join(", ")
  );
}

// =========================================================
// KI?U D? LI?U VÀ HÀM T?O VALIDATOR
// =========================================================

const UUID_PATTERN =
  "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$";

const LANGUAGE_PATTERN = "^[a-z]{2,3}(-[a-z0-9]{2,8})*$";

const ID = {
  bsonType: "string",
  pattern: UUID_PATTERN
};

const LANG = {
  bsonType: "string",
  pattern: LANGUAGE_PATTERN,
  maxLength: 35
};

const TEXT = { bsonType: "string" };
const NONEMPTY = { bsonType: "string", minLength: 1 };
const BOOL = { bsonType: "bool" };
const DATE = { bsonType: "date" };
const OBJECT = { bsonType: "object" };

const AUDIT = {
  created_at: DATE,
  updated_at: DATE
};

// S? nguyên không nh? hon min.
// Khi nh?p tr?c ti?p trong mongosh có th? dùng NumberInt/NumberLong.
const integer = (min = 0) => ({
  bsonType: ["int", "long"],
  minimum: min
});

const nullable = schema => ({
  anyOf: [schema, { bsonType: "null" }]
});

const values = (...items) => ({
  bsonType: "string",
  enum: items
});

function objectOf(properties) {
  return {
    bsonType: "object",
    required: Object.keys(properties),
    additionalProperties: false,
    properties
  };
}

// Object có các key là mã ngôn ng?:
// { vi: {...}, en: {...} }
function languageMap(itemSchema) {
  return {
    bsonType: "object",
    additionalProperties: false,
    patternProperties: {
      [LANGUAGE_PATTERN]: itemSchema
    }
  };
}

// GeoJSON Point: coordinates = [longitude, latitude].
const POINT = objectOf({
  type: values("Point"),
  coordinates: {
    bsonType: "array",
    minItems: 2,
    maxItems: 2,
    items: [
      {
        bsonType: ["double", "int", "long"],
        minimum: -180,
        maximum: 180
      },
      {
        bsonType: ["double", "int", "long"],
        minimum: -90,
        maximum: 90
      }
    ]
  }
});

const present = path => ({
  $ne: [{ $ifNull: [path, null] }, null]
});

const absent = path => ({
  $eq: [{ $ifNull: [path, null] }, null]
});

const orderedDates = (start, end) => ({
  $or: [
    absent(start),
    absent(end),
    { $gte: [end, start] }
  ]
});

// Ki?m tra m?t thu?c tính không b? trùng trong cùng m?t m?ng.
function uniqueArrayField(path, field) {
  return {
    $cond: [
      { $isArray: path },
      {
        $let: {
          vars: {
            items: {
              $map: {
                input: path,
                as: "item",
                in: "$$item." + field
              }
            }
          },
          in: {
            $eq: [
              { $size: "$$items" },
              {
                $size: {
                  $setUnion: ["$$items", []]
                }
              }
            ]
          }
        }
      },
      false
    ]
  };
}

// required: các thu?c tính b?t bu?c.
// optional: các thu?c tính có th? b? qua.
// expr: di?u ki?n b? sung gi?a các tru?ng trong document.
function create(
  name,
  required,
  optional = {},
  expr = null,
  idSchema = ID
) {
  const schemaRule = {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", ...Object.keys(required)],
      additionalProperties: false,
      properties: {
        _id: idSchema,
        ...required,
        ...optional
      }
    }
  };

  appDb.createCollection(name, {
    validator: expr
      ? { $and: [schemaRule, { $expr: expr }] }
      : schemaRule,

    validationLevel: "strict",
    validationAction: "error"
  });
}

// =========================================================
// 1. TÀI KHO?N QU?N TR?
// =========================================================

create("admin_users", {
  email: NONEMPTY,
  full_name: NONEMPTY,
  password_hash: NONEMPTY,
  is_active: BOOL,
  ...AUDIT
});

// =========================================================
// 2. NGÔN NG?
// _id s? d?ng mã ngôn ng?: vi, en...
// =========================================================

create("languages", {
  name: NONEMPTY,
  native_name: NONEMPTY,
  is_enabled: BOOL,
  ...AUDIT
}, {}, null, LANG);

// =========================================================
// 3. POI
// published_contents gi? c?p n?i dung/audio dang phát hành.
// Ví d?: published_contents.vi, published_contents.en
// =========================================================

const publication = objectOf({
  content_id: ID,
  audio_asset_id: ID,
  published_at: DATE,
  published_by: ID
});

create("pois", {
  code: NONEMPTY,

  category: values(
    "attraction",
    "food",
    "bus_stop",
    "other"
  ),

  address: TEXT,
  location: POINT,

  radius_enter_m: integer(1),
  radius_exit_m: integer(1),
  cooldown_seconds: integer(),
  priority: integer(),

  status: values("draft", "active", "archived"),
  revision: integer(1),

  published_contents: languageMap(publication),

  created_by: ID,
  ...AUDIT
}, {
  image_key: nullable(TEXT)
}, {
  $gt: ["$radius_exit_m", "$radius_enter_m"]
});

// =========================================================
// 4. N?I DUNG THEO NGÔN NG? VÀ PHIÊN B?N
// approved là dã duy?t; b?n dang phát hành n?m trong POI.
// =========================================================

create("poi_contents", {
  poi_id: ID,
  language_code: LANG,
  version: integer(1),

  title: NONEMPTY,
  description: TEXT,
  narration_text: NONEMPTY,

  review_status: values("draft", "approved", "archived"),

  created_by: ID,
  ...AUDIT
}, {
  source_content_id: nullable(ID),
  reviewed_at: nullable(DATE)
}, {
  $and: [
    {
      $ne: [
        "$_id",
        { $ifNull: ["$source_content_id", null] }
      ]
    },
    {
      $or: [
        { $ne: ["$review_status", "approved"] },
        present("$reviewed_at")
      ]
    }
  ]
});

// =========================================================
// 5. FILE AUDIO ÐÃ HOÀN T?T
// MP3 n?m trong storage; document luu metadata.
// =========================================================

create("audio_assets", {
  poi_content_id: ID,
  source_type: values("upload", "tts"),

  storage_key: NONEMPTY,
  duration_ms: integer(1),
  file_size_bytes: integer(1),
  mime_type: NONEMPTY,

  sha256: {
    bsonType: "string",
    pattern: "^[0-9a-f]{64}$"
  },

  created_at: DATE
}, {
  provider: nullable(NONEMPTY),
  voice_id: nullable(NONEMPTY)
}, {
  $or: [
    { $eq: ["$source_type", "upload"] },
    {
      $and: [
        present("$provider"),
        present("$voice_id")
      ]
    }
  ]
});

// =========================================================
// 6. TOUR
// translations: object theo ngôn ng?.
// stops: m?ng di?m d?ng, t?i da 100 di?m trong thi?t k? này.
// =========================================================

create("tours", {
  code: NONEMPTY,
  estimated_duration_minutes: integer(),

  status: values("draft", "published", "archived"),
  content_revision: integer(1),

  translations: languageMap(
    objectOf({
      title: NONEMPTY,
      description: TEXT
    })
  ),

  stops: {
    bsonType: "array",
    maxItems: 100,
    items: objectOf({
      poi_id: ID,
      stop_order: integer(1)
    })
  },

  created_by: ID,
  ...AUDIT
}, {}, {
  $and: [
    uniqueArrayField("$stops", "poi_id"),
    uniqueArrayField("$stops", "stop_order")
  ]
});

// =========================================================
// 7. MÃ QR
// Payload: tourguide://qr/<_id>
// =========================================================

create("qr_codes", {
  poi_id: ID,
  label: NONEMPTY,
  is_active: BOOL,
  ...AUDIT
});

// =========================================================
// 8. TÁC V? D?CH THU?T / TTS
// =========================================================

create("content_jobs", {
  job_type: values("translate", "tts"),
  input_content_id: ID,

  provider: NONEMPTY,
  parameters: OBJECT,

  status: values(
    "queued",
    "running",
    "succeeded",
    "failed"
  ),

  attempts: integer(),
  max_attempts: integer(1),

  idempotency_key: NONEMPTY,
  requested_by: ID,

  ...AUDIT
}, {
  target_language_code: nullable(LANG),

  output_content_id: nullable(ID),
  output_audio_id: nullable(ID),

  next_retry_at: nullable(DATE),
  error_message: nullable(TEXT),

  started_at: nullable(DATE),
  finished_at: nullable(DATE)
}, {
  $and: [
    {
      $lte: ["$attempts", "$max_attempts"]
    },
    {
      $or: [
        {
          $and: [
            { $eq: ["$job_type", "translate"] },
            present("$target_language_code"),
            absent("$output_audio_id")
          ]
        },
        {
          $and: [
            { $eq: ["$job_type", "tts"] },
            absent("$target_language_code"),
            absent("$output_content_id")
          ]
        }
      ]
    },
    {
      $or: [
        { $ne: ["$status", "succeeded"] },
        {
          $and: [
            { $eq: ["$job_type", "translate"] },
            present("$output_content_id")
          ]
        },
        {
          $and: [
            { $eq: ["$job_type", "tts"] },
            present("$output_audio_id")
          ]
        }
      ]
    },
    orderedDates("$started_at", "$finished_at")
  ]
});

// =========================================================
// 9. GÓI OFFLINE
// manifest là snapshot d? li?u và danh sách file c?n t?i.
// =========================================================

create("tour_packages", {
  tour_id: ID,
  language_code: LANG,
  source_revision: integer(1),

  manifest: OBJECT,
  total_bytes: integer(),

  created_at: DATE
});

// =========================================================
// 10. PHIÊN THAM QUAN
// Không có tour_id n?u khách khám phá t? do.
// =========================================================

create("visit_sessions", {
  initial_language_code: LANG,
  started_at: DATE,
  ...AUDIT
}, {
  tour_id: nullable(ID),
  ended_at: nullable(DATE)
}, orderedDates("$started_at", "$ended_at"));

// =========================================================
// 11. LU?T NGHE
// =========================================================

create("playbacks", {
  session_id: ID,
  audio_asset_id: ID,

  trigger_type: values("gps", "qr", "manual"),

  status: values(
    "pending",
    "playing",
    "paused",
    "completed",
    "stopped",
    "failed"
  ),

  listened_ms: integer(),
  last_event_seq: integer(),

  ...AUDIT
}, {
  qr_code_id: nullable(ID),
  started_at: nullable(DATE),
  ended_at: nullable(DATE)
}, {
  $and: [
    {
      $or: [
        {
          $and: [
            { $eq: ["$trigger_type", "qr"] },
            present("$qr_code_id")
          ]
        },
        {
          $and: [
            { $ne: ["$trigger_type", "qr"] },
            absent("$qr_code_id")
          ]
        }
      ]
    },
    orderedDates("$started_at", "$ended_at"),
    {
      $or: [
        {
          $not: [
            {
              $in: [
                "$status",
                ["playing", "paused", "completed", "stopped"]
              ]
            }
          ]
        },
        present("$started_at")
      ]
    },
    {
      $or: [
        {
          $not: [
            {
              $in: [
                "$status",
                ["completed", "stopped", "failed"]
              ]
            }
          ]
        },
        present("$ended_at")
      ]
    }
  ]
});

// =========================================================
// 12. S? KI?N NGHE
// Gi? nguyên _id và seq_no khi g?i l?i d? li?u offline.
// =========================================================

create("playback_events", {
  playback_id: ID,
  seq_no: integer(1),

  event_type: values(
    "start",
    "progress",
    "pause",
    "resume",
    "seek",
    "complete",
    "stop",
    "error"
  ),

  listened_ms_total: integer(),
  position_ms: integer(),

  occurred_at: DATE,
  received_at: DATE
});

// =========================================================
// 13. M? R?NG: M?U V? TRÍ GPS
// =========================================================

create("location_samples", {
  session_id: ID,
  location: POINT,

  accuracy_m: {
    bsonType: ["double", "int", "long"],
    minimum: 0,
    maximum: 10000000
  },

  recorded_at: DATE,
  received_at: DATE
});

// =========================================================
// CH? M?C
// MongoDB dã có unique index cho _id.
// =========================================================

function index(name, keys, options = {}) {
  appDb.getCollection(name).createIndex(keys, options);
}

// Email duy nh?t, không phân bi?t hoa/thu?ng.
index("admin_users", { email: 1 }, {
  unique: true,
  name: "uq_admin_email",
  collation: {
    locale: "en",
    strength: 2
  }
});

index("pois", { code: 1 }, {
  unique: true
});

index("pois", {
  location: "2dsphere"
});

index("poi_contents", {
  poi_id: 1,
  language_code: 1,
  version: 1
}, {
  unique: true
});

index("poi_contents", {
  source_content_id: 1
});

index("audio_assets", { storage_key: 1 }, {
  unique: true
});

index("audio_assets", {
  poi_content_id: 1
});

index("tours", { code: 1 }, {
  unique: true
});

index("tours", {
  "stops.poi_id": 1
});

index("qr_codes", {
  poi_id: 1
});

index("content_jobs", { idempotency_key: 1 }, {
  unique: true
});

index("content_jobs", {
  status: 1,
  created_at: 1
});

index("content_jobs", {
  input_content_id: 1
});

index("tour_packages", {
  tour_id: 1,
  language_code: 1,
  source_revision: 1
}, {
  unique: true
});

index("visit_sessions", {
  tour_id: 1,
  started_at: 1
});

index("playbacks", {
  session_id: 1,
  started_at: 1
});

index("playbacks", {
  audio_asset_id: 1,
  started_at: 1
});

index("playbacks", {
  qr_code_id: 1
});

index("playbacks", {
  started_at: 1
});

index("playback_events", {
  playback_id: 1,
  seq_no: 1
}, {
  unique: true
});

index("location_samples", {
  session_id: 1,
  recorded_at: 1
});

index("location_samples", {
  location: "2dsphere"
});

// =========================================================
// D? LI?U DANH M?C BAN Ð?U
// =========================================================

const seedTime = new Date();

appDb.getCollection("languages").insertMany([
  {
    _id: "vi",
    name: "Vietnamese",
    native_name: "Ti?ng Vi?t",
    is_enabled: true,
    created_at: seedTime,
    updated_at: seedTime
  },
  {
    _id: "en",
    name: "English",
    native_name: "English",
    is_enabled: true,
    created_at: seedTime,
    updated_at: seedTime
  }
]);

print("Ðã kh?i t?o database tour_guide v?i 13 collections.");