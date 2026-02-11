"""Data models for BentWookie V2."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Project:
    """Represents a BentWookie project."""

    prjname: str
    prjid: int | None = None
    prjphase: str = "define"
    prjdesc: str | None = None
    prjcodedir: str | None = None
    prjmodel: str | None = None
    prjmaxagents: int = 5
    prjtouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """Create a Project from a database row dict."""
        return cls(
            prjid=data.get("prjid"),
            prjname=data["prjname"],
            prjphase=data.get("prjphase", "define"),
            prjdesc=data.get("prjdesc"),
            prjcodedir=data.get("prjcodedir"),
            prjmodel=data.get("prjmodel"),
            prjmaxagents=data.get("prjmaxagents", 5),
            prjtouchts=data.get("prjtouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "prjid": self.prjid,
            "prjname": self.prjname,
            "prjphase": self.prjphase,
            "prjdesc": self.prjdesc,
            "prjcodedir": self.prjcodedir,
            "prjmodel": self.prjmodel,
            "prjmaxagents": self.prjmaxagents,
            "prjtouchts": self.prjtouchts,
        }


@dataclass
class Component:
    """Represents a component in the project hierarchy."""

    prjid: int
    cmpname: str
    cmplevel: str
    cmpid: int | None = None
    parent_id: int | None = None
    cmpstatus: str = "draft"
    cmpdesc: str | None = None
    cmpspec: str | None = None
    is_collapsed: int = 0
    cmporder: int = 0
    cmptouchts: datetime | None = None
    # Joined fields
    children: list["Component"] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Component":
        """Create a Component from a database row dict."""
        return cls(
            cmpid=data.get("cmpid"),
            prjid=data["prjid"],
            parent_id=data.get("parent_id"),
            cmpname=data["cmpname"],
            cmplevel=data["cmplevel"],
            cmpstatus=data.get("cmpstatus", "draft"),
            cmpdesc=data.get("cmpdesc"),
            cmpspec=data.get("cmpspec"),
            is_collapsed=data.get("is_collapsed", 0),
            cmporder=data.get("cmporder", 0),
            cmptouchts=data.get("cmptouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "cmpid": self.cmpid,
            "prjid": self.prjid,
            "parent_id": self.parent_id,
            "cmpname": self.cmpname,
            "cmplevel": self.cmplevel,
            "cmpstatus": self.cmpstatus,
            "cmpdesc": self.cmpdesc,
            "cmpspec": self.cmpspec,
            "is_collapsed": self.is_collapsed,
            "cmporder": self.cmporder,
            "cmptouchts": self.cmptouchts,
        }


@dataclass
class ConnectionMap:
    """Represents a peer connection between components."""

    from_cmpid: int
    to_cmpid: int
    conid: int | None = None
    condesc: str | None = None
    contype: str = "data"
    contouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ConnectionMap":
        """Create a ConnectionMap from a database row dict."""
        return cls(
            conid=data.get("conid"),
            from_cmpid=data["from_cmpid"],
            to_cmpid=data["to_cmpid"],
            condesc=data.get("condesc"),
            contype=data.get("contype", "data"),
            contouchts=data.get("contouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "conid": self.conid,
            "from_cmpid": self.from_cmpid,
            "to_cmpid": self.to_cmpid,
            "condesc": self.condesc,
            "contype": self.contype,
            "contouchts": self.contouchts,
        }


@dataclass
class Dependency:
    """Represents a build-order DAG edge."""

    cmpid: int
    depends_on_cmpid: int
    depid: int | None = None
    deptouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Dependency":
        """Create a Dependency from a database row dict."""
        return cls(
            depid=data.get("depid"),
            cmpid=data["cmpid"],
            depends_on_cmpid=data["depends_on_cmpid"],
            deptouchts=data.get("deptouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "depid": self.depid,
            "cmpid": self.cmpid,
            "depends_on_cmpid": self.depends_on_cmpid,
            "deptouchts": self.deptouchts,
        }


@dataclass
class Agent:
    """Represents an agent instance."""

    prjid: int
    agtrole: str
    agtid: int | None = None
    agtstatus: str = "idle"
    agtname: str | None = None
    agtmodel: str | None = None
    agtshellpid: int | None = None
    agtcmpid: int | None = None
    agterror: str | None = None
    agtstarted: datetime | None = None
    agttouchts: datetime | None = None
    # Joined fields
    cmpname: str | None = None
    prjname: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Agent":
        """Create an Agent from a database row dict."""
        return cls(
            agtid=data.get("agtid"),
            prjid=data["prjid"],
            agtrole=data["agtrole"],
            agtstatus=data.get("agtstatus", "idle"),
            agtname=data.get("agtname"),
            agtmodel=data.get("agtmodel"),
            agtshellpid=data.get("agtshellpid"),
            agtcmpid=data.get("agtcmpid"),
            agterror=data.get("agterror"),
            agtstarted=data.get("agtstarted"),
            agttouchts=data.get("agttouchts"),
            cmpname=data.get("cmpname"),
            prjname=data.get("prjname"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "agtid": self.agtid,
            "prjid": self.prjid,
            "agtrole": self.agtrole,
            "agtstatus": self.agtstatus,
            "agtname": self.agtname,
            "agtmodel": self.agtmodel,
            "agtshellpid": self.agtshellpid,
            "agtcmpid": self.agtcmpid,
            "agterror": self.agterror,
            "agtstarted": self.agtstarted,
            "agttouchts": self.agttouchts,
        }


@dataclass
class AgentMessage:
    """Represents an inter-agent message."""

    to_agtid: int
    msgbody: str
    msgid: int | None = None
    from_agtid: int | None = None
    msgtype: str = "normal"
    msgstatus: str = "queued"
    msgtouchts: datetime | None = None
    # Joined fields
    from_name: str | None = None
    to_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        """Create an AgentMessage from a database row dict."""
        return cls(
            msgid=data.get("msgid"),
            from_agtid=data.get("from_agtid"),
            to_agtid=data["to_agtid"],
            msgtype=data.get("msgtype", "normal"),
            msgstatus=data.get("msgstatus", "queued"),
            msgbody=data["msgbody"],
            msgtouchts=data.get("msgtouchts"),
            from_name=data.get("from_name"),
            to_name=data.get("to_name"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "msgid": self.msgid,
            "from_agtid": self.from_agtid,
            "to_agtid": self.to_agtid,
            "msgtype": self.msgtype,
            "msgstatus": self.msgstatus,
            "msgbody": self.msgbody,
            "msgtouchts": self.msgtouchts,
        }


@dataclass
class Interview:
    """Represents an interview session."""

    prjid: int
    itvtype: str
    itvid: int | None = None
    itvstatus: str = "pending"
    itvsummary: str | None = None
    itvtouchts: datetime | None = None
    # Joined fields
    prjname: str | None = None
    message_count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "Interview":
        """Create an Interview from a database row dict."""
        return cls(
            itvid=data.get("itvid"),
            prjid=data["prjid"],
            itvtype=data["itvtype"],
            itvstatus=data.get("itvstatus", "pending"),
            itvsummary=data.get("itvsummary"),
            itvtouchts=data.get("itvtouchts"),
            prjname=data.get("prjname"),
            message_count=data.get("message_count", 0),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "itvid": self.itvid,
            "prjid": self.prjid,
            "itvtype": self.itvtype,
            "itvstatus": self.itvstatus,
            "itvsummary": self.itvsummary,
            "itvtouchts": self.itvtouchts,
        }


@dataclass
class InterviewMessage:
    """Represents a message within an interview."""

    itvid: int
    imsgsender: str
    imsgcontent: str
    imsgid: int | None = None
    imsgtouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "InterviewMessage":
        """Create an InterviewMessage from a database row dict."""
        return cls(
            imsgid=data.get("imsgid"),
            itvid=data["itvid"],
            imsgsender=data["imsgsender"],
            imsgcontent=data["imsgcontent"],
            imsgtouchts=data.get("imsgtouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "imsgid": self.imsgid,
            "itvid": self.itvid,
            "imsgsender": self.imsgsender,
            "imsgcontent": self.imsgcontent,
            "imsgtouchts": self.imsgtouchts,
        }


@dataclass
class TestSpec:
    """Represents a test specification."""

    cmpid: int
    tsname: str
    tsid: int | None = None
    tsdesc: str | None = None
    tstype: str = "unit"
    tsstatus: str = "draft"
    tstouchts: datetime | None = None
    # Joined fields
    cmpname: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TestSpec":
        """Create a TestSpec from a database row dict."""
        return cls(
            tsid=data.get("tsid"),
            cmpid=data["cmpid"],
            tsname=data["tsname"],
            tsdesc=data.get("tsdesc"),
            tstype=data.get("tstype", "unit"),
            tsstatus=data.get("tsstatus", "draft"),
            tstouchts=data.get("tstouchts"),
            cmpname=data.get("cmpname"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "tsid": self.tsid,
            "cmpid": self.cmpid,
            "tsname": self.tsname,
            "tsdesc": self.tsdesc,
            "tstype": self.tstype,
            "tsstatus": self.tsstatus,
            "tstouchts": self.tstouchts,
        }


@dataclass
class BuildTask:
    """Represents a work item for Phase 4."""

    cmpid: int
    btid: int | None = None
    agtid: int | None = None
    bttype: str = "implement"
    btstatus: str = "pending"
    btprompt: str | None = None
    btresult: str | None = None
    bterror: str | None = None
    bttouchts: datetime | None = None
    # Joined fields
    cmpname: str | None = None
    agtname: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "BuildTask":
        """Create a BuildTask from a database row dict."""
        return cls(
            btid=data.get("btid"),
            cmpid=data["cmpid"],
            agtid=data.get("agtid"),
            bttype=data.get("bttype", "implement"),
            btstatus=data.get("btstatus", "pending"),
            btprompt=data.get("btprompt"),
            btresult=data.get("btresult"),
            bterror=data.get("bterror"),
            bttouchts=data.get("bttouchts"),
            cmpname=data.get("cmpname"),
            agtname=data.get("agtname"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "btid": self.btid,
            "cmpid": self.cmpid,
            "agtid": self.agtid,
            "bttype": self.bttype,
            "btstatus": self.btstatus,
            "btprompt": self.btprompt,
            "btresult": self.btresult,
            "bterror": self.bterror,
            "bttouchts": self.bttouchts,
        }


@dataclass
class BuildPlan:
    """Represents a design phase plan for a component."""

    cmpid: int
    bpcontent: str
    bpid: int | None = None
    bpstatus: str = "draft"
    bptouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "BuildPlan":
        """Create a BuildPlan from a database row dict."""
        return cls(
            bpid=data.get("bpid"),
            cmpid=data["cmpid"],
            bpcontent=data["bpcontent"],
            bpstatus=data.get("bpstatus", "draft"),
            bptouchts=data.get("bptouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "bpid": self.bpid,
            "cmpid": self.cmpid,
            "bpcontent": self.bpcontent,
            "bpstatus": self.bpstatus,
            "bptouchts": self.bptouchts,
        }


@dataclass
class DesignAmendment:
    """Represents a rework protocol log entry."""

    cmpid: int
    dareason: str
    dachange: str
    daid: int | None = None
    agtid: int | None = None
    datouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "DesignAmendment":
        """Create a DesignAmendment from a database row dict."""
        return cls(
            daid=data.get("daid"),
            cmpid=data["cmpid"],
            agtid=data.get("agtid"),
            dareason=data["dareason"],
            dachange=data["dachange"],
            datouchts=data.get("datouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "daid": self.daid,
            "cmpid": self.cmpid,
            "agtid": self.agtid,
            "dareason": self.dareason,
            "dachange": self.dachange,
            "datouchts": self.datouchts,
        }


@dataclass
class Traceability:
    """Represents a business goal to component mapping."""

    prjid: int
    trcgoal: str
    trcid: int | None = None
    cmpid: int | None = None
    trcdesc: str | None = None
    trctouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Traceability":
        """Create a Traceability from a database row dict."""
        return cls(
            trcid=data.get("trcid"),
            prjid=data["prjid"],
            cmpid=data.get("cmpid"),
            trcgoal=data["trcgoal"],
            trcdesc=data.get("trcdesc"),
            trctouchts=data.get("trctouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "trcid": self.trcid,
            "prjid": self.prjid,
            "cmpid": self.cmpid,
            "trcgoal": self.trcgoal,
            "trcdesc": self.trcdesc,
            "trctouchts": self.trctouchts,
        }


@dataclass
class Learning:
    """Represents a learning/note for a project."""

    prjid: int
    lrndesc: str
    lrnid: int | None = None
    lrnsource: str | None = None
    lrnphase: str | None = None
    lrntouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Learning":
        """Create a Learning from a database row dict."""
        return cls(
            lrnid=data.get("lrnid"),
            prjid=data["prjid"],
            lrndesc=data["lrndesc"],
            lrnsource=data.get("lrnsource"),
            lrnphase=data.get("lrnphase"),
            lrntouchts=data.get("lrntouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "lrnid": self.lrnid,
            "prjid": self.prjid,
            "lrndesc": self.lrndesc,
            "lrnsource": self.lrnsource,
            "lrnphase": self.lrnphase,
            "lrntouchts": self.lrntouchts,
        }


@dataclass
class DaemonState:
    """Represents the orchestrator daemon state."""

    pid: int | None = None
    dsstatus: str = "stopped"
    dsphase: str | None = None
    dsproject_id: int | None = None
    started_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "DaemonState":
        """Create a DaemonState from a database row dict."""
        return cls(
            pid=data.get("pid"),
            dsstatus=data.get("dsstatus", "stopped"),
            dsphase=data.get("dsphase"),
            dsproject_id=data.get("dsproject_id"),
            started_at=data.get("started_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "pid": self.pid,
            "dsstatus": self.dsstatus,
            "dsphase": self.dsphase,
            "dsproject_id": self.dsproject_id,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Document:
    """Represents a generated artifact."""

    prjid: int
    docname: str
    docpath: str
    docid: int | None = None
    cmpid: int | None = None
    doctype: str | None = None
    docphase: str | None = None
    doctouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        """Create a Document from a database row dict."""
        return cls(
            docid=data.get("docid"),
            prjid=data["prjid"],
            cmpid=data.get("cmpid"),
            docname=data["docname"],
            docpath=data["docpath"],
            doctype=data.get("doctype"),
            docphase=data.get("docphase"),
            doctouchts=data.get("doctouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "docid": self.docid,
            "prjid": self.prjid,
            "cmpid": self.cmpid,
            "docname": self.docname,
            "docpath": self.docpath,
            "doctype": self.doctype,
            "docphase": self.docphase,
            "doctouchts": self.doctouchts,
        }


@dataclass
class TestResult:
    """Represents a test execution result."""

    tsid: int
    trid: int | None = None
    agtid: int | None = None
    trpassed: int = 0
    troutput: str | None = None
    trerror: str | None = None
    trtouchts: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TestResult":
        """Create a TestResult from a database row dict."""
        return cls(
            trid=data.get("trid"),
            tsid=data["tsid"],
            agtid=data.get("agtid"),
            trpassed=data.get("trpassed", 0),
            troutput=data.get("troutput"),
            trerror=data.get("trerror"),
            trtouchts=data.get("trtouchts"),
        )

    def to_dict(self) -> dict:
        """Convert to a dict for database operations."""
        return {
            "trid": self.trid,
            "tsid": self.tsid,
            "agtid": self.agtid,
            "trpassed": self.trpassed,
            "troutput": self.troutput,
            "trerror": self.trerror,
            "trtouchts": self.trtouchts,
        }
