#!/usr/bin/env python3
"""
Experimental retrofitting of SQLAlchemy model to existing table,using "tags" as
it is a relatively simple table.

For now I'm only interested in read-only functionality and TBH I'm not planning
on switching to using models in this repo, I just want to remind myself how
SQLAlchemy's ORM works.

Standalone usage (although this is primarily intended for module/library use):

  python3 models/tags.py science

References:
https://docs.sqlalchemy.org/en/13/orm/tutorial.html
"""

# import pdb

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

class Tag(Base):
    __tablename__ = 'tags'

    id = Column('tag_id', Integer, primary_key=True)
    name = Column('tag_name', String) # tinytext
    status = Column('tag_status', Integer) # tinyint(1)

    @property
    def mapping_details(self):
        """
        Returns a tuple of 3 integers:
        * Total mapping uses
        * Total number of distinct titles using this tag
        * Total number of distinct users using this tag
        """
        # This requires the Tag.mappings relationship that's defined a bit
        # further down after TagMapping
        mappings = self.mappings
        title_ids = set([z.title_id for z in mappings])
        user_ids = set([z.user_id for z in mappings])
        return len(mappings), len(title_ids), len(user_ids)

    def __repr__(self):
        return f'Tag "{self.name}" (ID #{self.id}, status={self.status})'

    @property
    def details(self):
        """
        Enhanced version of __repr__ that includes use counts at the expense
        of extra database overhead.
        Q: How (much) can that be mitigated by using eager lookup?
        """
        counts = self.mapping_details
        return f'{self} has {counts[0]} total mappings over {counts[1]} titles ' + \
            f'by {counts[2]} users'

class TagMapping(Base):
    __tablename__ = 'tag_mapping'

    id = Column('tagmap_id', Integer, primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.tag_id'))
    title_id = Column(Integer, ForeignKey('titles.title_id'))
    user_id = Column(Integer, ForeignKey('mw_user.user__id'))
    tag = relationship('Tag', back_populates='mappings')

    def __repr__(self):
        return f'TagMapping #{self.id}: tag={self.tag_id}; ' + \
            f'title={self.title_id}; user={self.user_id} '


Tag.mappings = relationship('TagMapping', order_by=TagMapping.id,
                            back_populates='tag')


if __name__ == '__main__':
    # Example dumping out all the tags, optionally filtering them
    import sys
    from sqlalchemy.orm import sessionmaker
    from common import get_connection

    conn = get_connection()
    Session = sessionmaker(bind=conn.engine)
    session = Session()

    tag_query = session.query(Tag)
    if len(sys.argv) > 1:
        tag_query = tag_query.filter(Tag.name.like(f'%{sys.argv[1]}%'))

    for t in tag_query.order_by(Tag.name):
        # TODO (maybe) have arg handling to only do details if explicitly requested?
        print(t.details)



