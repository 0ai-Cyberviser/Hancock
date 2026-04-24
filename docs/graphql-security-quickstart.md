# GraphQL Security Module - Quick Start Guide

## Overview
The GraphQL Security Module is a comprehensive educational framework for understanding, testing, and remediating GraphQL authentication and authorization vulnerabilities. It's designed for security professionals conducting authorized penetration testing and security assessments.

## What's Included

### 1. Knowledge Base (`collectors/graphql_security_kb.py`)
A curated collection of 9 detailed Q&A pairs covering:
- **IDOR/BOLA Detection**: How to identify and test for Broken Object Level Authorization
- **JWT Security**: Testing for algorithm confusion, weak secrets, and key confusion attacks
- **Field-Level Authorization**: Best practices for securing sensitive GraphQL fields
- **Mutation Testing**: How to test for authorization bypass in GraphQL mutations
- **Rate Limiting**: Techniques for testing and implementing rate limits
- **Security Tools**: Overview of essential GraphQL security testing tools
- **Remediation**: Production-safe remediation strategies with phased rollout

**Generate training data:**
```bash
python collectors/graphql_security_kb.py
# Output: data/raw_graphql_security_kb.json
```

### 2. Security Testing Framework (`collectors/graphql_security_tester.py`)
An automated testing tool for GraphQL endpoints featuring:
- **Introspection Testing**: Check if schema introspection is enabled
- **IDOR Detection**: Test for cross-account data access vulnerabilities
- **Batch IDOR Testing**: Test multiple IDs using GraphQL aliases
- **JWT Algorithm Confusion**: Test for `alg: none` and weak algorithms
- **Mutation Authorization**: Verify ownership validation in mutations
- **Field-Level Authorization**: Check if sensitive fields are properly protected
- **Rate Limiting**: Test authentication rate limits
- **Report Generation**: Comprehensive JSON security assessment reports

**Usage:**
```bash
# Basic test (requires authorization)
python collectors/graphql_security_tester.py \
  --url https://api.example.com/graphql \
  --token <your-jwt-token> \
  --verbose

# Generate report
python collectors/graphql_security_tester.py \
  --url https://api.example.com/graphql \
  --token <your-jwt-token> \
  --report security_report.json
```

**⚠️ IMPORTANT:** Only test systems you have explicit written authorization to test. Unauthorized testing is illegal.

### 3. Implementation Guide (`docs/graphql-security-guide.md`)
Complete security implementation guide with production-ready code:

**TypeScript/Node.js (Apollo Server):**
- Authentication context setup with JWT validation
- Secure resolvers with ownership checks
- Field-level authorization for sensitive data
- Mass assignment protection
- Rate limiting and complexity controls
- Server configuration hardening

**Python (Strawberry GraphQL):**
- Permission classes for authentication and authorization
- Context-aware field resolvers
- Role-based access control
- Secure mutation handlers

**Testing:**
- Automated security test examples
- CI/CD integration patterns

**Deployment:**
- Pre-deployment security checklist
- Post-deployment monitoring
- CloudWatch/DataDog query examples

### 4. Test Suite (`tests/test_graphql_security.py`)
Comprehensive test coverage with 16 unit tests:
- KB structure validation
- Content quality checks
- Security coverage verification
- Tool functionality tests

**Run tests:**
```bash
python -m unittest tests.test_graphql_security -v
```

## Integration with Hancock

The GraphQL Security Module integrates seamlessly with Hancock's existing architecture:

1. **Knowledge Base Integration**: The module follows the same pattern as other collectors (pentest_kb.py, soc_kb.py)
2. **Training Data**: Generated data can be included in future Hancock training datasets
3. **Educational Content**: All content emphasizes authorized testing and responsible disclosure

## Key Security Vulnerabilities Covered

### 1. IDOR/BOLA (HIGH Severity)
**Vulnerability:** API allows users to access other users' data by manipulating object IDs
**Test:** Try accessing `user(id: "other_user_id")` with your token
**Fix:** Implement ownership validation: `context.user.id === resourceUserId`

### 2. Missing Field-Level Authorization (HIGH Severity)
**Vulnerability:** Sensitive fields (email, SSN) exposed without proper checks
**Test:** Query for another user's sensitive fields
**Fix:** Add field-level resolvers that check ownership before returning data

### 3. JWT Algorithm Confusion (CRITICAL Severity)
**Vulnerability:** Server accepts `alg: none` or weak algorithms
**Test:** Create token with `alg: none` and remove signature
**Fix:** Explicitly whitelist strong algorithms (RS256, ES256) in JWT verification

### 4. Mutation Authorization Bypass (CRITICAL Severity)
**Vulnerability:** Mutations lack ownership validation
**Test:** Try updating/deleting another user's data
**Fix:** Require ownership check before executing mutations

### 5. Weak Rate Limiting (MEDIUM Severity)
**Vulnerability:** No limits on authentication attempts or expensive queries
**Test:** Send 50+ rapid login requests
**Fix:** Implement per-IP and per-user rate limits (< 10 attempts/min)

## Example Scenarios

### Scenario 1: Testing for IDOR
```bash
# 1. Authenticate as User A
curl -X POST https://api.example.com/graphql \
  -H "Authorization: Bearer <user-a-token>" \
  -d '{"query":"{ viewer { id } }"}'
# Response: {"data":{"viewer":{"id":"user_a_123"}}}

# 2. Try accessing User B's data
curl -X POST https://api.example.com/graphql \
  -H "Authorization: Bearer <user-a-token>" \
  -d '{"query":"{ user(id: \"user_b_456\") { email } }"}'

# VULNERABLE if returns User B's email
# SECURE if returns: {"errors":[{"message":"Access denied"}]}
```

### Scenario 2: Implementing Secure Authorization
```typescript
// BAD: No authorization check
const resolvers = {
  Query: {
    user: (parent, { id }) => db.users.findOne({ id })
  }
};

// GOOD: Ownership validation
const resolvers = {
  Query: {
    user: (parent, { id }, context) => {
      if (!context.user) {
        throw new AuthenticationError('Not authenticated');
      }
      if (context.user.id !== id && !context.user.roles.includes('ADMIN')) {
        throw new ForbiddenError('Access denied');
      }
      return db.users.findOne({ id });
    }
  }
};
```

## Best Practices Checklist

- [ ] Implement authentication checks in all resolvers
- [ ] Validate ownership (context.user.id === resourceUserId)
- [ ] Add field-level authorization for sensitive data
- [ ] Use strong JWT algorithms (RS256/ES256 only)
- [ ] Replace sequential IDs with UUIDs or opaque tokens
- [ ] Implement rate limiting (< 100 req/min per IP)
- [ ] Enable query depth limiting (max depth: 7)
- [ ] Disable introspection in production
- [ ] Disable GraphQL Playground in production
- [ ] Log and alert on cross-account access attempts
- [ ] Implement persisted queries for production
- [ ] Add security regression tests to CI/CD
- [ ] Sanitize error messages (no internal details)

## Resources

### Documentation
- [GraphQL Security Guide](../docs/graphql-security-guide.md)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)

### Testing Tools
- **InQL**: Burp Suite extension for GraphQL introspection
- **GraphQL Cop**: Automated security auditor (`pip install graphql-cop`)
- **BatchQL**: IDOR testing tool
- **Clairvoyance**: Schema reconstruction when introspection is disabled
- **GraphQL Voyager**: Schema visualization

### Community
- Report bugs: [GitHub Issues](https://github.com/cyberviser/Hancock/issues)
- Security contact: 0ai@cyberviserai.com
- Contributing: [CONTRIBUTING.md](../CONTRIBUTING.md)

## Legal & Ethical Notice

**This module is for educational purposes and authorized security testing only.**

✅ DO:
- Test systems you have explicit written permission to test
- Follow responsible disclosure practices
- Document findings professionally
- Recommend remediation strategies

❌ DON'T:
- Test systems without authorization (ILLEGAL)
- Exploit vulnerabilities beyond proof-of-concept
- Access, modify, or delete data unnecessarily
- Disclose vulnerabilities publicly before remediation

**Unauthorized access to computer systems is a crime under:**
- Computer Fraud and Abuse Act (CFAA) - USA
- Computer Misuse Act - UK
- Cybercrime Convention - Europe
- Similar laws in most countries worldwide

## Support

For questions, issues, or security concerns:
- **GitHub Issues**: https://github.com/cyberviser/Hancock/issues
- **Security Email**: 0ai@cyberviserai.com
- **Documentation**: https://github.com/cyberviser/Hancock/tree/main/docs

---

**Built by CyberViser · Hancock v0.6.0 · 2026-03-01**
