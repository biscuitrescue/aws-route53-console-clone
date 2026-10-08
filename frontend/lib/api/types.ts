import type { components } from "./schema";

type Schemas = components["schemas"];

export type User = Schemas["UserOut"];
export type Session = Schemas["SessionOut"];

export type ZoneType = Schemas["ZoneType"];
export type HostedZoneSummary = Schemas["HostedZoneSummary"];
export type HostedZone = Schemas["HostedZoneDetail"];
export type HostedZoneCreate = Schemas["HostedZoneCreate"];
export type Tag = Schemas["Tag"];
export type VpcAssociation = Schemas["VpcAssociation"];

export type RecordType = Schemas["RecordType"];
export type RoutingPolicy = Schemas["RoutingPolicy"];
export type RecordSet = Schemas["RecordSetOut"];
export type RecordSetInput = Schemas["RecordSetInput"];
export type RecordSetUpdate = Schemas["RecordSetUpdate"];
export type Change = Schemas["Change"];
export type ChangeBatchResult = Schemas["ChangeBatchResult"];

export type ZoneFileImportResult = Schemas["ZoneFileImportResult"];
export type ImportedRecordSet = Schemas["ImportedRecordSet"];
