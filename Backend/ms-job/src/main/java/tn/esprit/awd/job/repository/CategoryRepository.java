package tn.esprit.awd.job.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import tn.esprit.awd.job.entity.Category;

public interface CategoryRepository extends JpaRepository<Category, Long> {

    boolean existsByNameIgnoreCase(String name);

    boolean existsByNameIgnoreCaseAndIdNot(String name, Long id);
}
