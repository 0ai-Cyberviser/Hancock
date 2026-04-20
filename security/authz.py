#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Hancock Authorization Module — Scope-based authorization for agentic operations.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class Scope(BaseModel):
    """Authorization scope for agentic operations."""
    name: str
    metadata: dict = Field(default_factory=dict)
