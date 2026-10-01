// MongoDB initialization script for NIM Sentinel
// Run with: mongosh < mongo-init.js

// Switch to application database
db = db.getSiblingDB('nim_sentinel');

// Create collections with validation
db.createCollection('documents', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['tenant_id', 'filename', 'content_type', 'status', 'created_at'],
      properties: {
        tenant_id: { bsonType: 'string' },
        filename: { bsonType: 'string' },
        content_type: { bsonType: 'string' },
        status: { enum: ['pending', 'processing', 'completed', 'failed'] },
        created_at: { bsonType: 'date' },
        updated_at: { bsonType: 'date' },
        metadata: { bsonType: 'object' },
      },
    },
  },
});

db.createCollection('chunks', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['document_id', 'tenant_id', 'content', 'embedding', 'chunk_index', 'created_at'],
      properties: {
        document_id: { bsonType: 'objectId' },
        tenant_id: { bsonType: 'string' },
        content: { bsonType: 'string' },
        embedding: { bsonType: 'array', items: { bsonType: 'double' } },
        chunk_index: { bsonType: 'int' },
        metadata: { bsonType: 'object' },
        created_at: { bsonType: 'date' },
      },
    },
  },
});

db.createCollection('sessions', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_id', 'tenant_id', 'created_at'],
      properties: {
        user_id: { bsonType: 'string' },
        tenant_id: { bsonType: 'string' },
        title: { bsonType: 'string' },
        metadata: { bsonType: 'object' },
        created_at: { bsonType: 'date' },
        updated_at: { bsonType: 'date' },
      },
    },
  },
});

db.createCollection('checkpoints', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['thread_id', 'checkpoint', 'metadata', 'created_at'],
      properties: {
        thread_id: { bsonType: 'string' },
        checkpoint_ns: { bsonType: 'string' },
        checkpoint: { bsonType: 'object' },
        metadata: { bsonType: 'object' },
        parent_checkpoint_id: { bsonType: 'string' },
        created_at: { bsonType: 'date' },
      },
    },
  },
});

db.createCollection('long_term_memory', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_id', 'tenant_id', 'content', 'embedding', 'created_at'],
      properties: {
        user_id: { bsonType: 'string' },
        tenant_id: { bsonType: 'string' },
        content: { bsonType: 'string' },
        embedding: { bsonType: 'array', items: { bsonType: 'double' } },
        metadata: { bsonType: 'object' },
        created_at: { bsonType: 'date' },
        expires_at: { bsonType: 'date' },
      },
    },
  },
});

db.createCollection('audit_logs', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['action', 'user_id', 'resource', 'resource_id', 'outcome', 'timestamp'],
      properties: {
        action: { bsonType: 'string' },
        user_id: { bsonType: 'string' },
        tenant_id: { bsonType: 'string' },
        resource: { bsonType: 'string' },
        resource_id: { bsonType: 'string' },
        outcome: { bsonType: 'string' },
        details: { bsonType: 'object' },
        timestamp: { bsonType: 'date' },
      },
    },
  },
});

db.createCollection('eval_results', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['component', 'metric', 'value', 'threshold', 'passed', 'timestamp'],
      properties: {
        component: { bsonType: 'string' },
        metric: { bsonType: 'string' },
        value: { bsonType: 'double' },
        threshold: { bsonType: 'double' },
        passed: { bsonType: 'bool' },
        details: { bsonType: 'object' },
        timestamp: { bsonType: 'date' },
        git_sha: { bsonType: 'string' },
        environment: { bsonType: 'string' },
      },
    },
  },
});

db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['username', 'email', 'hashed_password', 'roles', 'created_at'],
      properties: {
        username: { bsonType: 'string' },
        email: { bsonType: 'string' },
        hashed_password: { bsonType: 'string' },
        roles: { bsonType: 'array', items: { bsonType: 'string' } },
        tenant_id: { bsonType: 'string' },
        is_active: { bsonType: 'bool' },
        created_at: { bsonType: 'date' },
        last_login: { bsonType: 'date' },
      },
    },
  },
});

db.createCollection('api_keys', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['key_hash', 'user_id', 'name', 'created_at'],
      properties: {
        key_hash: { bsonType: 'string' },
        user_id: { bsonType: 'string' },
        name: { bsonType: 'string' },
        scopes: { bsonType: 'array', items: { bsonType: 'string' } },
        expires_at: { bsonType: 'date' },
        created_at: { bsonType: 'date' },
        last_used: { bsonType: 'date' },
      },
    },
  },
});

// Create indexes
// Documents
db.documents.createIndex({ tenant_id: 1, created_at: -1 });
db.documents.createIndex({ tenant_id: 1, status: 1 });
db.documents.createIndex({ tenant_id: 1, filename: 'text' });

// Chunks - Vector search index (requires Atlas Vector Search)
// db.chunks.createIndex({ embedding: 'cosmosSearch' }, { name: 'vector_index' });
db.chunks.createIndex({ document_id: 1, chunk_index: 1 });
db.chunks.createIndex({ tenant_id: 1, created_at: -1 });
db.chunks.createIndex({ tenant_id: 1, 'metadata.doc_type': 1 });

// Sessions
db.sessions.createIndex({ user_id: 1, created_at: -1 });
db.sessions.createIndex({ tenant_id: 1, created_at: -1 });

// Checkpoints
db.checkpoints.createIndex({ thread_id: 1, created_at: -1 });
db.checkpoints.createIndex({ thread_id: 1, checkpoint_ns: 1 });

// Long-term memory
db.long_term_memory.createIndex({ user_id: 1, created_at: -1 });
db.long_term_memory.createIndex({ tenant_id: 1, created_at: -1 });
db.long_term_memory.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });

// Audit logs
db.audit_logs.createIndex({ user_id: 1, timestamp: -1 });
db.audit_logs.createIndex({ tenant_id: 1, timestamp: -1 });
db.audit_logs.createIndex({ resource: 1, resource_id: 1, timestamp: -1 });
db.audit_logs.createIndex({ timestamp: 1 }, { expireAfterSeconds: 2592000 }); // 30 days TTL

// Eval results
db.eval_results.createIndex({ component: 1, timestamp: -1 });
db.eval_results.createIndex({ timestamp: 1 }, { expireAfterSeconds: 7776000 }); // 90 days TTL

// Users
db.users.createIndex({ username: 1 }, { unique: true });
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ tenant_id: 1 });

// API Keys
db.api_keys.createIndex({ key_hash: 1 }, { unique: true });
db.api_keys.createIndex({ user_id: 1 });
db.api_keys.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });

// Create application user
db.createUser({
  user: 'nim_sentinel_app',
  pwd: 'changeme',
  roles: [
    { role: 'readWrite', db: 'nim_sentinel' },
  ],
});

print('NIM Sentinel database initialized successfully!');