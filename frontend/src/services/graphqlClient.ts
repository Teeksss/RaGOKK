// Last reviewed: 2025-04-30 12:17:45 UTC (User: Teeksssdevam et.)
import { GraphQLClient } from 'graphql-request';
import { useQuery, useMutation } from 'react-query';
import { getSdk } from './generated/graphql';
import { errorHandlingService } from './errorHandlingService';

// GraphQL Client yapılandırması
const endpoint = process.env.REACT_APP_GRAPHQL_ENDPOINT || '/graphql';

export const graphqlClient = new GraphQLClient(endpoint, {
  headers: () => {
    const token = localStorage.getItem('auth_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  },
});

// Generate typed SDK
export const sdk = getSdk(graphqlClient);

// Custom GraphQL Query Hook
export function useGraphQLQuery<TData, TVariables>(
  queryName: string,
  query: (variables: TVariables) => Promise<TData>,
  variables?: TVariables,
  options?: any
) {
  return useQuery<TData>(
    [queryName, variables],
    () => query(variables as TVariables),
    {
      onError: (error: any) => {
        errorHandlingService.handleError({
          message: error?.response?.errors?.[0]?.message || 'GraphQL query error',
          details: {
            query: queryName,
            variables,
            errors: error?.response?.errors
          }
        });
      },
      ...options,
    }
  );
}

// Custom GraphQL Mutation Hook
export function useGraphQLMutation<TData, TVariables>(
  mutationName: string,
  mutation: (variables: TVariables) => Promise<TData>,
  options?: any
) {
  return useMutation<TData, Error, TVariables>(
    (variables) => mutation(variables),
    {
      onError: (error: any) => {
        errorHandlingService.handleError({
          message: error?.response?.errors?.[0]?.message || 'GraphQL mutation error',
          details: {
            mutation: mutationName,
            errors: error?.response?.errors
          }
        });
      },
      ...options,
    }
  );
}

// Data Visualization için özel GraphQL Query Hook'ları
export function useDocumentStats(period: string = 'week', options?: any) {
  return useGraphQLQuery(
    'documentStats',
    () => sdk.GetDocumentStats({ period }),
    { period },
    options
  );
}

export function useQueryStats(period: string = 'week', options?: any) {
  return useGraphQLQuery(
    'queryStats',
    () => sdk.GetQueryStats({ period }),
    { period },
    options
  );
}

export function useUserActivities(userId: string, limit: number = 10, options?: any) {
  return useGraphQLQuery(
    'userActivities',
    () => sdk.GetUserActivities({ userId, limit }),
    { userId, limit },
    options
  );
}

export function useDocumentRelationships(documentId: string, options?: any) {
  return useGraphQLQuery(
    'documentRelationships',
    () => sdk.GetDocumentRelationships({ documentId }),
    { documentId },
    options
  );
}

export function useSystemMetrics(period: string = 'day', options?: any) {
  return useGraphQLQuery(
    'systemMetrics',
    () => sdk.GetSystemMetrics({ period }),
    { period },
    options
  );
}