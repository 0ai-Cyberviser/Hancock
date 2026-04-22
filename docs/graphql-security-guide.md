# GraphQL Authentication & Authorization Security Guide

## Overview
This guide provides comprehensive remediation strategies for GraphQL authentication and authorization vulnerabilities, specifically focusing on IDOR/BOLA (Broken Object Level Authorization) flaws identified in production GraphQL APIs.

## Table of Contents
1. [Common Vulnerabilities](#common-vulnerabilities)
2. [Secure Implementation Examples](#secure-implementation-examples)
3. [Testing & Validation](#testing--validation)
4. [Deployment Checklist](#deployment-checklist)

---

## Common Vulnerabilities

### 1. Missing Object-Level Authorization (IDOR/BOLA)
**Vulnerability:** API allows authenticated users to access other users' data by manipulating object IDs.

**Example Attack:**
```graphql
query {
  # Attacker is user_abc, but can access user_123's data
  user(id: "user_123") {
    email
    phone
    address
  }
}
```

**Impact:** HIGH - Account enumeration, data exfiltration, privacy breach

---

### 2. Missing Field-Level Authorization
**Vulnerability:** Sensitive fields lack authorization checks even when object access is controlled.

**Example Attack:**
```graphql
query {
  publicProfile(id: "user_123") {
    name          # Public - OK
    email         # Should be restricted!
    ssn           # Should be restricted!
  }
}
```

**Impact:** HIGH - Sensitive data exposure

---

### 3. JWT Algorithm Confusion
**Vulnerability:** Server accepts weak or manipulated JWT algorithms (e.g., `alg: none`).

**Example Attack:**
```bash
# Modify JWT header to use "none" algorithm, remove signature
eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhZG1pbiJ9.
```

**Impact:** CRITICAL - Complete authentication bypass

---

### 4. Mutation Authorization Bypass
**Vulnerability:** Mutations lack ownership validation, allowing cross-account modifications.

**Example Attack:**
```graphql
mutation {
  updateUser(id: "victim_123", input: { email: "attacker@evil.com" }) {
    id email
  }
}
```

**Impact:** CRITICAL - Account takeover, data manipulation

---

## Secure Implementation Examples

### TypeScript (Node.js + Apollo Server)

#### 1. Authentication Context Setup
```typescript
// lib/auth.ts
import jwt from 'jsonwebtoken';
import { AuthenticationError, ForbiddenError } from 'apollo-server';

export interface User {
  id: string;
  email: string;
  roles: string[];
}

export interface Context {
  user: User | null;
  ip: string;
}

/**
 * Verify JWT token and return user payload
 * Rejects tokens with weak/none algorithms
 */
export const verifyToken = (token: string): User | null => {
  try {
    // Explicitly specify allowed algorithms (prevent alg:none)
    const payload = jwt.verify(token, process.env.JWT_SECRET!, {
      algorithms: ['RS256', 'ES256'], // Only allow asymmetric algorithms
      issuer: 'api.example.com',
      audience: 'graphql-api',
      maxAge: '15m', // Tokens expire after 15 minutes
    });
    
    return payload as User;
  } catch (err) {
    // Invalid signature, expired, or wrong algorithm
    return null;
  }
};

/**
 * Require authenticated user in context
 */
export const requireAuth = (context: Context): User => {
  if (!context.user) {
    throw new AuthenticationError('Authentication required');
  }
  return context.user;
};

/**
 * Check if current user owns the resource
 */
export const isOwner = (context: Context, resourceUserId: string): boolean => {
  return context.user?.id === resourceUserId;
};

/**
 * Check if current user has required role
 */
export const hasRole = (context: Context, ...roles: string[]): boolean => {
  if (!context.user) return false;
  return roles.some(role => context.user!.roles.includes(role));
};

/**
 * Require ownership or admin role
 */
export const requireOwnerOrAdmin = (context: Context, resourceUserId: string): void => {
  const user = requireAuth(context);
  if (!isOwner(context, resourceUserId) && !hasRole(context, 'ADMIN')) {
    // Log unauthorized access attempt
    console.warn('[SECURITY] Unauthorized access attempt', {
      actor: user.id,
      target: resourceUserId,
      ip: context.ip,
      timestamp: new Date().toISOString(),
    });
    throw new ForbiddenError('Access denied: not owner or admin');
  }
};
```

#### 2. Secure GraphQL Resolvers
```typescript
// resolvers/user.ts
import { requireAuth, requireOwnerOrAdmin, isOwner, hasRole } from '../lib/auth';
import type { Context } from '../lib/auth';

interface UserQueryArgs {
  id: string;
}

interface UpdateUserArgs {
  id: string;
  input: {
    email?: string;
    phone?: string;
    publicName?: string;
  };
}

const resolvers = {
  Query: {
    /**
     * Get current authenticated user (viewer pattern)
     */
    viewer: (parent: any, args: any, context: Context) => {
      const user = requireAuth(context);
      return db.users.findOne({ id: user.id });
    },
    
    /**
     * Get user by ID - requires ownership or admin
     */
    user: async (parent: any, { id }: UserQueryArgs, context: Context) => {
      requireAuth(context);
      
      const user = await db.users.findOne({ id });
      if (!user) {
        return null;
      }
      
      // Authorization check: only owner or admin can access
      requireOwnerOrAdmin(context, id);
      
      return user;
    },
    
    /**
     * List users - admin only
     */
    users: async (parent: any, args: any, context: Context) => {
      requireAuth(context);
      
      if (!hasRole(context, 'ADMIN')) {
        throw new ForbiddenError('Admin role required');
      }
      
      return db.users.find({});
    },
  },
  
  User: {
    /**
     * Field-level authorization for sensitive data
     * Returns null if user lacks permission (alternative: throw ForbiddenError)
     */
    email: (parent: any, args: any, context: Context) => {
      if (!isOwner(context, parent.id) && !hasRole(context, 'ADMIN')) {
        return null; // Hide email from non-owners
      }
      return parent.email;
    },
    
    phone: (parent: any, args: any, context: Context) => {
      if (!isOwner(context, parent.id) && !hasRole(context, 'ADMIN')) {
        return null; // Hide phone from non-owners
      }
      return parent.phone;
    },
    
    ssn: (parent: any, args: any, context: Context) => {
      // SSN requires admin role
      if (!hasRole(context, 'ADMIN')) {
        return null;
      }
      return parent.ssn;
    },
    
    publicName: (parent: any) => parent.publicName, // Always visible
  },
  
  Mutation: {
    /**
     * Update user - requires ownership or admin
     */
    updateUser: async (parent: any, { id, input }: UpdateUserArgs, context: Context) => {
      requireOwnerOrAdmin(context, id);
      
      // Mass assignment protection: only allow specific fields
      const { email, phone, publicName } = input;
      const safeInput = { email, phone, publicName };
      
      // Validate email format
      if (email && !isValidEmail(email)) {
        throw new Error('Invalid email format');
      }
      
      const updated = await db.users.update({ id }, safeInput);
      return updated;
    },
    
    /**
     * Delete user - requires ownership or admin
     */
    deleteUser: async (parent: any, { id }: { id: string }, context: Context) => {
      requireOwnerOrAdmin(context, id);
      
      await db.users.delete({ id });
      return true;
    },
  },
};

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default resolvers;
```

#### 3. Server Configuration
```typescript
// server.ts
import { ApolloServer } from 'apollo-server-express';
import express from 'express';
import depthLimit from 'graphql-depth-limit';
import { createComplexityLimitRule } from 'graphql-validation-complexity';
import rateLimit from 'express-rate-limit';
import { verifyToken } from './lib/auth';
import resolvers from './resolvers';
import typeDefs from './schema';

const app = express();

// Rate limiting middleware
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // 100 requests per window per IP
  message: 'Too many requests from this IP',
  standardHeaders: true,
  legacyHeaders: false,
});

app.use('/graphql', limiter);

const server = new ApolloServer({
  typeDefs,
  resolvers,
  
  // Context builder: extract user from JWT
  context: ({ req }): Context => {
    const authHeader = req.headers.authorization || '';
    const token = authHeader.replace('Bearer ', '').trim();
    
    const user = token ? verifyToken(token) : null;
    
    return {
      user,
      ip: req.ip || req.connection.remoteAddress || 'unknown',
    };
  },
  
  // Security configurations
  introspection: process.env.NODE_ENV !== 'production', // Disable in prod
  playground: process.env.NODE_ENV !== 'production',    // Disable in prod
  
  // Query complexity/depth limiting
  validationRules: [
    depthLimit(7), // Max query depth
    createComplexityLimitRule(1000, {
      scalarCost: 1,
      objectCost: 5,
      listFactor: 10,
    }),
  ],
  
  // Disable batched queries (prevents IDOR batching)
  allowBatchedHttpRequests: false,
  
  // Format errors (don't leak internal details)
  formatError: (err) => {
    console.error('[GraphQL Error]', err);
    
    if (process.env.NODE_ENV === 'production') {
      // Generic error message in production
      if (err.message.includes('Internal')) {
        return new Error('Internal server error');
      }
    }
    
    return err;
  },
});

await server.start();
server.applyMiddleware({ app, path: '/graphql' });

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`🚀 GraphQL server running on http://localhost:${PORT}/graphql`);
});
```

---

### Python (with Strawberry GraphQL)

#### 1. Authentication Setup
```python
# lib/auth.py
import jwt
from datetime import datetime, timedelta
from typing import Optional
from functools import wraps
from strawberry.permission import BasePermission
from strawberry.types import Info

class User:
    def __init__(self, id: str, email: str, roles: list[str]):
        self.id = id
        self.email = email
        self.roles = roles

class Context:
    def __init__(self, user: Optional[User], ip: str):
        self.user = user
        self.ip = ip

def verify_token(token: str) -> Optional[User]:
    """
    Verify JWT token with strict algorithm checks
    Rejects alg:none and other weak algorithms
    """
    try:
        payload = jwt.decode(
            token,
            key=os.getenv('JWT_SECRET'),
            algorithms=['RS256', 'ES256'],  # Only allow asymmetric
            issuer='api.example.com',
            audience='graphql-api',
            leeway=0,  # No clock skew tolerance
        )
        return User(
            id=payload['sub'],
            email=payload['email'],
            roles=payload.get('roles', [])
        )
    except jwt.InvalidTokenError:
        return None

class IsAuthenticated(BasePermission):
    """Permission class: require authentication"""
    message = "User must be authenticated"
    
    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        return info.context.user is not None

class IsOwnerOrAdmin(BasePermission):
    """Permission class: require ownership or admin role"""
    message = "Access denied: not owner or admin"
    
    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        if not info.context.user:
            return False
        
        # Get resource user ID from kwargs
        resource_user_id = kwargs.get('id') or kwargs.get('user_id')
        
        # Allow if owner or admin
        is_owner = info.context.user.id == resource_user_id
        is_admin = 'ADMIN' in info.context.user.roles
        
        if not (is_owner or is_admin):
            # Log unauthorized attempt
            print(f"[SECURITY] Unauthorized access: {info.context.user.id} -> {resource_user_id}")
        
        return is_owner or is_admin
```

#### 2. Secure Resolvers
```python
# resolvers/user.py
import strawberry
from typing import Optional
from strawberry.types import Info
from lib.auth import IsAuthenticated, IsOwnerOrAdmin, Context

@strawberry.type
class User:
    id: str
    public_name: str
    
    @strawberry.field
    def email(self, info: Info) -> Optional[str]:
        """Field-level auth: only owner or admin can see email"""
        context: Context = info.context
        
        if not context.user:
            return None
        
        # Check ownership or admin role
        is_owner = context.user.id == self.id
        is_admin = 'ADMIN' in context.user.roles
        
        if is_owner or is_admin:
            return self._email  # Return actual email
        return None  # Hide from others
    
    @strawberry.field
    def phone(self, info: Info) -> Optional[str]:
        """Field-level auth: only owner or admin can see phone"""
        context: Context = info.context
        
        if not context.user:
            return None
        
        is_owner = context.user.id == self.id
        is_admin = 'ADMIN' in context.user.roles
        
        if is_owner or is_admin:
            return self._phone
        return None

@strawberry.type
class Query:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def viewer(self, info: Info) -> Optional[User]:
        """Get current authenticated user"""
        context: Context = info.context
        user_data = db.get_user(context.user.id)
        return User(**user_data) if user_data else None
    
    @strawberry.field(permission_classes=[IsOwnerOrAdmin])
    def user(self, id: str, info: Info) -> Optional[User]:
        """Get user by ID - requires ownership or admin"""
        user_data = db.get_user(id)
        return User(**user_data) if user_data else None

@strawberry.input
class UserInput:
    email: Optional[str] = None
    phone: Optional[str] = None
    public_name: Optional[str] = None

@strawberry.type
class Mutation:
    @strawberry.mutation(permission_classes=[IsOwnerOrAdmin])
    def update_user(self, id: str, input: UserInput, info: Info) -> User:
        """Update user - requires ownership or admin"""
        # Mass assignment protection: only update allowed fields
        safe_data = {}
        if input.email:
            safe_data['email'] = input.email
        if input.phone:
            safe_data['phone'] = input.phone
        if input.public_name:
            safe_data['public_name'] = input.public_name
        
        updated = db.update_user(id, safe_data)
        return User(**updated)
```

---

## Testing & Validation

### Automated Security Tests
```typescript
// tests/graphql-security.test.ts
import { createTestClient } from 'apollo-server-testing';
import { ApolloServer } from 'apollo-server';
import { expect } from 'chai';

describe('GraphQL Security Tests', () => {
  let server: ApolloServer;
  let userAToken: string;
  let userBToken: string;
  
  before(async () => {
    // Setup test server
    server = new ApolloServer({ typeDefs, resolvers });
    
    // Create test users
    userAToken = await createTestUser('user_a@test.com');
    userBToken = await createTestUser('user_b@test.com');
  });
  
  describe('IDOR Protection', () => {
    it('should prevent cross-account data access', async () => {
      const { query } = createTestClient(server);
      
      // User A tries to access User B's data
      const result = await query({
        query: `
          query {
            user(id: "user_b_id") {
              email
            }
          }
        `,
        http: { headers: { authorization: `Bearer ${userAToken}` } },
      });
      
      expect(result.errors).to.exist;
      expect(result.errors[0].message).to.include('Access denied');
    });
    
    it('should allow users to access their own data', async () => {
      const { query } = createTestClient(server);
      
      const result = await query({
        query: `
          query {
            user(id: "user_a_id") {
              email
            }
          }
        `,
        http: { headers: { authorization: `Bearer ${userAToken}` } },
      });
      
      expect(result.errors).to.not.exist;
      expect(result.data.user.email).to.equal('user_a@test.com');
    });
  });
  
  describe('Field-Level Authorization', () => {
    it('should hide sensitive fields from non-owners', async () => {
      const { query } = createTestClient(server);
      
      const result = await query({
        query: `
          query {
            publicProfile(id: "user_b_id") {
              publicName
              email
            }
          }
        `,
        http: { headers: { authorization: `Bearer ${userAToken}` } },
      });
      
      expect(result.data.publicProfile.publicName).to.exist;
      expect(result.data.publicProfile.email).to.be.null; // Hidden
    });
  });
  
  describe('JWT Security', () => {
    it('should reject tokens with alg:none', async () => {
      const { query } = createTestClient(server);
      
      // Create fake token with alg:none
      const fakeToken = 'eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9.';
      
      const result = await query({
        query: `{ viewer { email } }`,
        http: { headers: { authorization: `Bearer ${fakeToken}` } },
      });
      
      expect(result.errors).to.exist;
      expect(result.errors[0].message).to.include('Authentication required');
    });
  });
});
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All resolvers have authentication checks
- [ ] Ownership validation implemented for all object queries
- [ ] Field-level authorization for sensitive data
- [ ] Mass assignment protection in mutations
- [ ] JWT uses only strong algorithms (RS256/ES256)
- [ ] Rate limiting configured (< 100 req/min per IP)
- [ ] Query depth limiting enabled (max depth: 7)
- [ ] Query complexity limiting enabled
- [ ] Introspection disabled in production
- [ ] GraphQL Playground disabled in production
- [ ] Error messages sanitized (no internal leaks)
- [ ] Batch queries disabled
- [ ] HTTPS enforced
- [ ] Security tests passing

### Post-Deployment
- [ ] Monitor for unauthorized access attempts
- [ ] Set up alerts for cross-account queries
- [ ] Enable CloudWatch/DataDog logging
- [ ] Run external security scan
- [ ] Schedule quarterly penetration tests
- [ ] Enable bug bounty program
- [ ] Document authorization patterns for developers

### Monitoring Queries
```sql
-- CloudWatch Insights: Detect IDOR attempts
fields @timestamp, @message
| filter @message like /Access denied: not owner/
| stats count() by user_id, ip
| sort count desc

-- Alert on suspicious patterns
fields @timestamp, user_id, target_user_id
| filter user_id != target_user_id
| stats count() by user_id
| filter count > 10
```

---

## Additional Resources
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [GraphQL Security Best Practices](https://graphql.org/learn/authorization/)
- [Apollo Server Security](https://www.apollographql.com/docs/apollo-server/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

---

**Security Contact:** 0ai@cyberviserai.com
**Last Updated:** 2026-03-01
