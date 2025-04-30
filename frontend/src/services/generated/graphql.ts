// Last reviewed: 2025-04-30 12:17:45 UTC (User: Teeksssdevam et.)
import { GraphQLClient } from 'graphql-request';
import { print } from 'graphql';
import gql from 'graphql-tag';

// GraphQL Şema
export type Maybe<T> = T | null;
export type InputMaybe<T> = Maybe<T>;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };

// Document Stats
export type DocumentStatsInput = {
  period: string;
};

export type DocumentStats = {
  __typename?: 'DocumentStats';
  totalDocuments: number;
  documentsByType: Array<DocumentTypeCount>;
  documentsOverTime: Array<DocumentTimePoint>;
  averageSize: number;
  topTags: Array<TagCount>;
};

export type DocumentTypeCount = {
  __typename?: 'DocumentTypeCount';
  type: string;
  count: number;
};

export type DocumentTimePoint = {
  __typename?: 'DocumentTimePoint';
  date: string;
  count: number;
};

export type TagCount = {
  __typename?: 'TagCount';
  tag: string;
  count: number;
};

// Query Stats
export type QueryStatsInput = {
  period: string;
};

export type QueryStats = {
  __typename?: 'QueryStats';
  totalQueries: number;
  queriesByType: Array<QueryTypeCount>;
  queriesOverTime: Array<QueryTimePoint>;
  averageResponseTime: number;
  topQueryTerms: Array<QueryTermCount>;
};

export type QueryTypeCount = {
  __typename?: 'QueryTypeCount';
  type: string;
  count: number;
};

export type QueryTimePoint = {
  __typename?: 'QueryTimePoint';
  date: string;
  count: number;
};

export type QueryTermCount = {
  __typename?: 'QueryTermCount';
  term: string;
  count: number;
};

// User Activities
export type UserActivitiesInput = {
  userId: string;
  limit: number;
};

export type UserActivity = {
  __typename?: 'UserActivity';
  id: string;
  userId: string;
  action: string;
  resourceType: string;
  resourceId?: Maybe<string>;
  details?: Maybe<string>;
  timestamp: string;
};

export type UserActivities = {
  __typename?: 'UserActivities';
  activities: Array<UserActivity>;
};

// Document Relationships
export type DocumentRelationshipsInput = {
  documentId: string;
};

export type DocumentRelationship = {
  __typename?: 'DocumentRelationship';
  sourceDocumentId: string;
  targetDocumentId: string;
  relationshipType: string;
  weight: number;
};

export type DocumentRelationships = {
  __typename?: 'DocumentRelationships';
  relationships: Array<DocumentRelationship>;
  documentInfo: DocumentInfo;
};

export type DocumentInfo = {
  __typename?: 'DocumentInfo';
  id: string;
  title: string;
  type: string;
  createdAt: string;
};

// System Metrics
export type SystemMetricsInput = {
  period: string;
};

export type SystemMetrics = {
  __typename?: 'SystemMetrics';
  cpuUsage: Array<MetricPoint>;
  memoryUsage: Array<MetricPoint>;
  diskUsage: Array<MetricPoint>;
  requestRate: Array<MetricPoint>;
  errorRate: Array<MetricPoint>;
  responseTime: Array<MetricPoint>;
};

export type MetricPoint = {
  __typename?: 'MetricPoint';
  timestamp: string;
  value: number;
};

// Queries
export type Query = {
  __typename?: 'Query';
  documentStats: DocumentStats;
  queryStats: QueryStats;
  userActivities: UserActivities;
  documentRelationships: DocumentRelationships;
  systemMetrics: SystemMetrics;
};

export type QueryDocumentStatsArgs = {
  input: DocumentStatsInput;
};

export type QueryQueryStatsArgs = {
  input: QueryStatsInput;
};

export type QueryUserActivitiesArgs = {
  input: UserActivitiesInput;
};

export type QueryDocumentRelationshipsArgs = {
  input: DocumentRelationshipsInput;
};

export type QuerySystemMetricsArgs = {
  input: SystemMetricsInput;
};

// Document Stats Query
export const GetDocumentStatsDocument = gql`
  query GetDocumentStats($period: String!) {
    documentStats(input: { period: $period }) {
      totalDocuments
      documentsByType {
        type
        count
      }
      documentsOverTime {
        date
        count
      }
      averageSize
      topTags {
        tag
        count
      }
    }
  }
`;

// Query Stats Query
export const GetQueryStatsDocument = gql`
  query GetQueryStats($period: String!) {
    queryStats(input: { period: $period }) {
      totalQueries
      queriesByType {
        type
        count
      }
      queriesOverTime {
        date
        count
      }
      averageResponseTime
      topQueryTerms {
        term
        count
      }
    }
  }
`;

// User Activities Query
export const GetUserActivitiesDocument = gql`
  query GetUserActivities($userId: String!, $limit: Int!) {
    userActivities(input: { userId: $userId, limit: $limit }) {
      activities {
        id
        userId
        action
        resourceType
        resourceId
        details
        timestamp
      }
    }
  }
`;

// Document Relationships Query
export const GetDocumentRelationshipsDocument = gql`
  query GetDocumentRelationships($documentId: String!) {
    documentRelationships(input: { documentId: $documentId }) {
      relationships {
        sourceDocumentId
        targetDocumentId
        relationshipType
        weight
      }
      documentInfo {
        id
        title
        type
        createdAt
      }
    }
  }
`;

// System Metrics Query
export const GetSystemMetricsDocument = gql`
  query GetSystemMetrics($period: String!) {
    systemMetrics(input: { period: $period }) {
      cpuUsage {
        timestamp
        value
      }
      memoryUsage {
        timestamp
        value
      }
      diskUsage {
        timestamp
        value
      }
      requestRate {
        timestamp
        value
      }
      errorRate {
        timestamp
        value
      }
      responseTime {
        timestamp
        value
      }
    }
  }
`;

export type SdkFunctionWrapper = <T>(action: (requestHeaders?: Record<string, string>) => Promise<T>, operationName: string) => Promise<T>;

const defaultWrapper: SdkFunctionWrapper = (action, _operationName) => action();

export function getSdk(client: GraphQLClient, withWrapper: SdkFunctionWrapper = defaultWrapper) {
  return {
    GetDocumentStats(variables: { period: string }, requestHeaders?: Record<string, string>): Promise<{ documentStats: DocumentStats }> {
      return withWrapper(() => client.request<{ documentStats: DocumentStats }>(print(GetDocumentStatsDocument), variables, requestHeaders), 'GetDocumentStats');
    },
    GetQueryStats(variables: { period: string }, requestHeaders?: Record<string, string>): Promise<{ queryStats: QueryStats }> {
      return withWrapper(() => client.request<{ queryStats: QueryStats }>(print(GetQueryStatsDocument), variables, requestHeaders), 'GetQueryStats');
    },
    GetUserActivities(variables: { userId: string, limit: number }, requestHeaders?: Record<string, string>): Promise<{ userActivities: UserActivities }> {
      return withWrapper(() => client.request<{ userActivities: UserActivities }>(print(GetUserActivitiesDocument), variables, requestHeaders), 'GetUserActivities');
    },
    GetDocumentRelationships(variables: { documentId: string }, requestHeaders?: Record<string, string>): Promise<{ documentRelationships: DocumentRelationships }> {
      return withWrapper(() => client.request<{ documentRelationships: DocumentRelationships }>(print(GetDocumentRelationshipsDocument), variables, requestHeaders), 'GetDocumentRelationships');
    },
    GetSystemMetrics(variables: { period: string }, requestHeaders?: Record<string, string>): Promise<{ systemMetrics: SystemMetrics }> {
      return withWrapper(() => client.request<{ systemMetrics: SystemMetrics }>(print(GetSystemMetricsDocument), variables, requestHeaders), 'GetSystemMetrics');
    }
  };
}
export type Sdk = ReturnType<typeof getSdk>;