# INTERFACES and STANDARDS
Common definition, program, or data interfaces you would like to enforce across the project.


## Project Directory
All code for this project should be saved somewhere in the `bentwookie/` directory.
All task files should be saved to the `tasks/` directory.


## Technical Glossary
- data type abbreviations:
    - **LOD**: list of dictionaries, i.e., `[{...},{...},]`
    - **LID**: list of IDs (usually UUIDs)
    - **SDF**: standard data format, a specific, self-describing json structure 


## Infrastructure
All code components should be deployed using the below AWS Microservices Architecture, using AWS serverless / hosted products whenever possible.  This bias towards hosted infra is aimed at speeding deployment and minimizing operational costs. 

- AuroraDB for persistent data 
- DynamoDB for caching or transient json data
- Lambda for compute
- Lambda Layer for consistency of said compute (always use layers when available) 
- Kinesis for data queuing / event management
- API Gateway to expose select lambda functions as APIs
- Route53 / Custom Domain Name for APIs (`https://api.paydaay.app/`)
- S3 for file storage
- SQS for short timers (under 15min)
- SNS for external notifications


## Standard Data Format (SDF)
A simple, self-describing json data object structure that can predictably pass data between various storage and compute components. 

The structure is comprised, at minimum, of two levels and three structures:
- **metadata**: information about the request, source, process, or usage.
- **metadata.data**: a substructure of metadata, this defines every data object outside of metadata, including datatype, hash, pagniation information, etc.
- **[all other data structures]**: all non-metadata top-level data structures. To be in compliance, all top-level data structures must be defined in metadata.data, with at least name and datatype.

Example: a single row returned from Postgres.

```json
{  "metadata": 
    {   "region": "us-east-1",
        "timestamp": "2023-01-01 00:00:00+00:00",
        "data": [ 
            {"name":"rows", "datatype":"lod", "pagination": ...}
            ]  
    },  
    "rows": [{...},{...},...]
}
```

A more complex example, containing multiple data sets, as seen at the end of the auction workflow. Note how each top-level object (except metadata) appears in the metadata.data definition, which includes at minimum `.name` and `.datatype`. 
```json
{  "metadata": 
    {   "prev_step": "validate clu",
        "next_step": "create_cpdo",
        "region": "us-east-1",
        "source": "AuroraDB",
        "timestamp": "2023-01-01 00:00:00+00:00",
        "employer": "00000000-0000-4000-8000-000000000000",
        "employee": "00000000-0000-4000-8000-000000000000",
        "data": [
            {"name":"id",      "datatype":"str",  ...},
            {"name":"version", "datatype":"str",  ...},
            {"name":"shift",   "datatype":"dict", ...},
            {"name":"clu",     "datatype":"dict", ...},
            {"name":"cpdo",    "datatype":"dict", ...},
            {"name":"auction", "datatype":"dict", ...},
            {"name":"bids",    "datatype":"lod",  ...},
            ]  
    },  
    "id": "00000000-0000-7000-8000-000000000000",
    "version": "00000000-0000-4000-8000-000000000000",
    "shift":  {...},
    "clu":    {...},  
    "cpdo":   {...},
    "auction":{...},
    "bids":  [{...},{...},...]
}
``` 


## Domain Names
- **paydaay.com** - public facing webpage 
- **api.paydaay.app** - core REST API URL