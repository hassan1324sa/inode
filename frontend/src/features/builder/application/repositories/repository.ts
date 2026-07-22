export interface Repository<T, Id> {
  getById(id: Id): Promise<T>;
  save(entity: T): Promise<void>;
  delete(id: Id): Promise<void>;
  list(): Promise<T[]>;
}
