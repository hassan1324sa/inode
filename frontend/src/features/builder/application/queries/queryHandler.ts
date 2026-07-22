export interface QueryHandler<Q, R> {
  execute(query: Q): Promise<R>;
}
