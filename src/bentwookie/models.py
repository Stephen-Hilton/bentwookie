"""Data models for BentWookie."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Project:
    """Represents a BentWookie project."""

    prjname: str
    prjid: int | None = None
    prjversion: str = "poc"
    prjpriority: int = 5
    prjphase: str = "dev"
    prjdesc: str | None = None
    prjtouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create a Project from a database row dict."""
        return cls(
            prjid=data.get("prjid"),
            prjname=data["prjname"],
            prjversion=data.get("prjversion", "poc"),
            prjpriority=data.get("prjpriority", 5),
            prjphase=data.get("prjphase", "dev"),
            prjdesc=data.get("prjdesc"),
            prjtouchts=data.get("prjtouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "prjid": self.prjid,
            "prjname": self.prjname,
            "prjversion": self.prjversion,
            "prjpriority": self.prjpriority,
            "prjphase": self.prjphase,
            "prjdesc": self.prjdesc,
            "prjtouchts": self.prjtouchts,
        }


@dataclass
class Request:
    """Represents a development request within a project."""

    prjid: int
    reqname: str
    reqprompt: str
    reqid: int | None = None
    reqtype: str = "new_feature"
    reqstatus: str = "tbd"
    reqphase: str = "plan"
    reqpriority: int = 5
    reqcodedir: str | None = None
    reqdocpath: str | None = None
    reqtouchts: datetime | None = None
    # Joined fields
    prjname: str | None = None
    project_phase: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Request":
        """Create a Request from a database row dict."""
        return cls(
            reqid=data.get("reqid"),
            prjid=data["prjid"],
            reqname=data["reqname"],
            reqprompt=data["reqprompt"],
            reqtype=data.get("reqtype", "new_feature"),
            reqstatus=data.get("reqstatus", "tbd"),
            reqphase=data.get("reqphase", "plan"),
            reqpriority=data.get("reqpriority", 5),
            reqcodedir=data.get("reqcodedir"),
            reqdocpath=data.get("reqdocpath"),
            reqtouchts=data.get("reqtouchts"),
            prjname=data.get("prjname"),
            project_phase=data.get("project_phase"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "reqid": self.reqid,
            "prjid": self.prjid,
            "reqname": self.reqname,
            "reqprompt": self.reqprompt,
            "reqtype": self.reqtype,
            "reqstatus": self.reqstatus,
            "reqphase": self.reqphase,
            "reqpriority": self.reqpriority,
            "reqcodedir": self.reqcodedir,
            "reqdocpath": self.reqdocpath,
            "reqtouchts": self.reqtouchts,
        }


@dataclass
class Infrastructure:
    """Represents infrastructure configuration for a project."""

    prjid: int
    inftype: str
    infid: int | None = None
    infprovider: str = "local"
    infval: str | None = None
    infnote: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Infrastructure":
        """Create an Infrastructure from a database row dict."""
        return cls(
            infid=data.get("infid"),
            prjid=data["prjid"],
            inftype=data["inftype"],
            infprovider=data.get("infprovider", "local"),
            infval=data.get("infval"),
            infnote=data.get("infnote"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "infid": self.infid,
            "prjid": self.prjid,
            "inftype": self.inftype,
            "infprovider": self.infprovider,
            "infval": self.infval,
            "infnote": self.infnote,
        }


@dataclass
class Learning:
    """Represents a learning/note for a project."""

    prjid: int
    lrndesc: str
    lrnid: int | None = None
    lrntouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Learning":
        """Create a Learning from a database row dict."""
        return cls(
            lrnid=data.get("lrnid"),
            prjid=data["prjid"],
            lrndesc=data["lrndesc"],
            lrntouchts=data.get("lrntouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "lrnid": self.lrnid,
            "prjid": self.prjid,
            "lrndesc": self.lrndesc,
            "lrntouchts": self.lrntouchts,
        }


@dataclass
class DaemonStatus:
    """Represents the current status of the daemon."""

    running: bool = False
    current_request_id: int | None = None
    current_phase: str | None = None
    started_at: datetime | None = None
    last_activity: datetime | None = None
    requests_processed: int = 0
    errors_count: int = 0
