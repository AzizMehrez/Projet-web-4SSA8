package tn.esprit.awd.job.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import tn.esprit.awd.job.entity.Job;

import java.util.List;

public interface JobRepository extends JpaRepository<Job, Long> {

    /** Optional filters: null means "no filter". Category is fetched to avoid N+1. */
    @Query("""
            select j from Job j join fetch j.category c
            where (:available is null or j.available = :available)
              and (:categoryId is null or c.id = :categoryId)
            order by j.date desc, j.id desc
            """)
    List<Job> search(@Param("available") Boolean available, @Param("categoryId") Long categoryId);

    boolean existsByCategoryId(Long categoryId);
}
